# -*- coding: utf-8 -*-
"""Step E: Strictly read-only 5-page electrical & style verification for NVmw single-channel v1.

NEVER calls eda.sch_Netlist.getNetlist() or getNetlistFile().
"""
import json
import math
import re
import sys

sys.path.insert(0, r'c:\Users\Jo1yc\Desktop\硕士课题\_agent_tmp')
from nvmw_lib import POWER_PAGE_UUID, PA_PAGE_UUID, SIGN_PAGE_UUID, dump_page, get_pages, js, open_page

REPORT_PATH = r'c:\Users\Jo1yc\Desktop\硕士课题\_agent_tmp\nvmw_v1_verify_report.json'


def iter_wire_segs(ln):
    """Yield (x0, y0, x1, y1) from EasyEDA w['line'] (4-number segment chunks)."""
    if len(ln) >= 4 and len(ln) % 4 == 0:
        for i in range(0, len(ln), 4):
            p0 = (round(ln[i], 2), round(ln[i + 1], 2))
            p1 = (round(ln[i + 2], 2), round(ln[i + 3], 2))
            if p0 != p1:
                yield p0[0], p0[1], p1[0], p1[1]
    else:
        for i in range(0, len(ln) - 2, 2):
            p0 = (round(ln[i], 2), round(ln[i + 1], 2))
            p1 = (round(ln[i + 2], 2), round(ln[i + 3], 2))
            if p0 != p1:
                yield p0[0], p0[1], p1[0], p1[1]


def on_seg(px, py, x0, y0, x1, y1, tol=0.2):
    if abs(x0 - x1) < tol and abs(px - x0) < tol:
        return min(y0, y1) - tol <= py <= max(y0, y1) + tol
    if abs(y0 - y1) < tol and abs(py - y0) < tol:
        return min(x0, x1) - tol <= px <= max(x0, x1) + tol
    return False


def build_page_graph(pg):
    """Build geometric wire/flag/port/pin T-junction union-find graph (read-only)."""
    parent = {}

    def find(k):
        while parent.setdefault(k, k) != k:
            parent[k] = parent[parent[k]]
            k = parent[k]
        return k

    def union(a, b):
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[ra] = rb

    segs = []
    for w in pg['wires']:
        net = (w['net'] or '').strip()
        for x0, y0, x1, y1 in iter_wire_segs(w['line']):
            p0 = (round(x0, 1), round(y0, 1))
            p1 = (round(x1, 1), round(y1, 1))
            segs.append((p0, p1))
            union(p0, p1)
            if net:
                union(p0, ('NET', net))

    for fl in pg['flags']:
        pt = (round(fl['x'], 1), round(fl['y'], 1))
        parent.setdefault(pt, pt)
        net = (fl['net'] or '').strip()
        if net:
            union(pt, ('NET', net))

    for c in pg['reals']:
        for _, _, px, py, _ in c['pins']:
            pt = (round(px, 1), round(py, 1))
            parent.setdefault(pt, pt)

    pts = [k for k in list(parent) if isinstance(k, tuple) and isinstance(k[0], (int, float))]
    for pt in pts:
        for p0, p1 in segs:
            if on_seg(pt[0], pt[1], p0[0], p0[1], p1[0], p1[1]):
                union(pt, p0)

    rnames_exact = {}
    rnames_upper = {}
    for k in list(parent):
        if isinstance(k, tuple) and k[0] == 'NET':
            r = find(k)
            rnames_exact.setdefault(r, set()).add(k[1])
            rnames_upper.setdefault(r, set()).add(k[1].upper())

    return find, segs, rnames_exact, rnames_upper


def check_offgrid(pg, segs):
    """Detect pins near wires without exact snapping (0.02..5.0); track all separately."""
    offgrid = []
    for c in pg['reals']:
        for pn, pnm, px, py, _ in c['pins']:
            best = 999.0
            for p0, p1 in segs:
                if abs(p0[0] - p1[0]) < 0.15 and min(p0[1], p1[1]) - 0.15 <= py <= max(p0[1], p1[1]) + 0.15:
                    best = min(best, abs(px - p0[0]))
                elif abs(p0[1] - p1[1]) < 0.15 and min(p0[0], p1[0]) - 0.15 <= px <= max(p0[0], p1[0]) + 0.15:
                    best = min(best, abs(py - p0[1]))
                best = min(best, math.hypot(px - p0[0], py - p0[1]), math.hypot(px - p1[0], py - p1[1]))
            if 0.02 < best < 5.0:
                offgrid.append((c['des'], str(pn), str(pnm), round(best, 3)))
    return offgrid


def pin_net_map(c, find, rnames_exact, rnames_upper):
    out = {}
    for pn, pnm, px, py, _ in c['pins']:
        pt = (round(px, 1), round(py, 1))
        r = find(pt)
        out[str(pn)] = {
            'name': str(pnm),
            'exact': sorted(rnames_exact.get(r, set())),
            'upper': sorted(rnames_upper.get(r, set())),
        }
    return out


def run():
    pages = get_pages()
    page_names = [p['name'] for p in pages]
    page_by_name = {p['name']: p['uuid'] for p in pages}
    print("1. Pages:", pages)

    expected_names = {'sign', 'power', 'PA_REF', 'REF_CLOCK', 'CLOCK_DIST'}
    pages_ok = set(page_names) == expected_names and len(pages) == 5

    dumps = {}
    graphs = {}
    for p in pages:
        pg = dump_page(p['uuid'])
        dumps[p['name']] = pg
        find, segs, rex, rup = build_page_graph(pg)
        graphs[p['name']] = {
            'find': find, 'segs': segs, 'rex': rex, 'rup': rup,
            'offgrid': check_offgrid(pg, segs),
        }
        print(f"   {p['name']:10s} ({p['uuid']}): reals={len(pg['reals']):3d}, flags={len(pg['flags']):3d}, wires={len(pg['wires']):3d}, rects={len(pg['rects'])}, texts={len(pg['texts'])}, offgrid={len(graphs[p['name']]['offgrid'])}")

    # 2. Global designator uniqueness across BOM/PCB components & PA_REF isolation
    bom_pcb_des = {}
    pa_bad_flags = []
    u17_found = []
    for pname, pg in dumps.items():
        for c in pg['reals']:
            des = c['des']
            if des == 'U17' or 'HMC349' in (c['nm'] or '').upper():
                u17_found.append((pname, des, c['nm']))
            if pname == 'PA_REF':
                if c['bom'] or c['pcb']:
                    pa_bad_flags.append((des, c['bom'], c['pcb']))
            elif c['bom'] or c['pcb']:
                bom_pcb_des.setdefault(des, []).append((pname, c.get('sub'), c['nm']))

    allowed_multi = {'U5', 'U303', 'U222'}
    des_collisions = {d: v for d, v in bom_pcb_des.items() if len(v) > 1 and d not in allowed_multi}

    # Check sub-units for multi-unit ICs
    print(f"2. PA_REF bom/pcb violations: {pa_bad_flags}, U17 found: {u17_found}")
    print(f"   Designator collisions (excluding multi-unit {sorted(allowed_multi)}): {des_collisions}")
    for md in sorted(allowed_multi):
        print(f"   Multi-unit {md}: {len(bom_pcb_des.get(md, []))} instances -> {[x[0] for x in bom_pcb_des.get(md, [])]}")

    # 3. Zero legacy artifacts
    legacy_nets = {'AGND', '5vpa', '3V3osc', 'VCC_12v', 'vcc12', '3v3_sw', 'CFLY_P', 'CFLY_M'}
    legacy_des = {'U17', 'R58', 'R59', 'R15', 'R17', 'R62', 'C128', 'C129'}
    found_legacy_nets = []
    found_legacy_des = []
    for pname, pg in dumps.items():
        for f in pg['flags']:
            if (f['net'] or '') in legacy_nets:
                found_legacy_nets.append((pname, 'flag', f['net'], f['x'], f['y']))
        for w in pg['wires']:
            if (w['net'] or '') in legacy_nets:
                found_legacy_nets.append((pname, 'wire', w['net']))
        for c in pg['reals']:
            if pname != 'PA_REF' and c['des'] in legacy_des:
                found_legacy_des.append((pname, c['des'], c['nm']))
    print(f"3. Legacy nets: {found_legacy_nets}, Legacy designators: {found_legacy_des}")

    # 4. Per-page shorts, offgrid, floating pins
    per_page_report = {}
    ref_allowed_nc = {('U224', '1')}
    clk_allowed_nc = {
        ('U225', 'OUT2+'), ('U225', 'OUT2–'), ('U225', 'OUT2-'),
        ('U226', 'IN1_P'), ('U226', 'IN1_N'), ('U226', 'VAC_REF0'), ('U226', 'VAC_REF1'),
        ('U226', 'OUT6_P'), ('U226', 'OUT6_N'), ('U226', 'OUT7_P'), ('U226', 'OUT7_N'),
        ('U228', 'Q0'), ('U228', 'Q1'), ('U228', 'Q3'),
        ('U233', 'N.C'),
    }
    pwr_new_des = {'U304', 'U305', 'C321', 'C322', 'C323', 'C324', 'C325'}
    sign_new_des = {
        'U301', 'U302', 'U303', 'D301', 'C311', 'C312', 'C313', 'C314', 'C315', 'C316',
        'C317', 'C318', 'C319', 'C320', 'R300', 'R301', 'R302', 'R303', 'R304', 'R305',
        'R306', 'R307', 'R308', 'R309', 'R310', 'J_RFOUT', 'H1',
        'U14', 'C120', 'C121', 'C122', 'C123',
    }
    sign_h1_spares = {str(n) for n in (11, 13, 19, 21, 22, 31, 33, 35, 37)}

    for pname, pg in dumps.items():
        g = graphs[pname]
        find, rex, rup = g['find'], g['rex'], g['rup']
        shorts_upper = []
        case_diffs = []
        for r, uset in rup.items():
            if len(uset) > 1:
                shorts_upper.append(sorted(uset))
        for r, eset in rex.items():
            if len(eset) > 1 and len(rup[r]) == 1:
                case_diffs.append(sorted(eset))

        # Count pins per connected root for anonymous point-to-point wires (e.g. U304 <-> C322 flying cap)
        root_pin_cnt = {}
        for c in pg['reals']:
            for _, _, px, py, _ in c['pins']:
                r = find((round(px, 1), round(py, 1)))
                root_pin_cnt[r] = root_pin_cnt.get(r, 0) + 1

        floating = []
        for c in pg['reals']:
            des = c['des']
            check_this = (
                pname in ('REF_CLOCK', 'CLOCK_DIST', 'PA_REF')
                or (pname == 'power' and des in pwr_new_des)
                or (pname == 'sign' and des in sign_new_des)
            )
            if not check_this:
                continue
            for pn, pnm, px, py, _ in c['pins']:
                pn_s, pnm_s = str(pn), str(pnm)
                if pname == 'REF_CLOCK' and (des, pn_s) in ref_allowed_nc:
                    continue
                if pname == 'CLOCK_DIST' and (des, pnm_s) in clk_allowed_nc:
                    continue
                if pname == 'power' and des == 'U305' and pn_s == '4':
                    continue
                if pname == 'sign' and des == 'H1' and pn_s in sign_h1_spares:
                    continue
                if pname == 'sign' and des == 'U301' and pnm_s.upper() == 'NC':
                    continue
                if pname == 'sign' and des == 'U14' and pn_s in {'6', '7', '13', '15'}:
                    continue
                r = find((round(px, 1), round(py, 1)))
                ns = rup.get(r, set())
                if len(ns) == 0:
                    # Direct anonymous internal point-to-point links (e.g. U304<->C322, R247<->C248, U228<->U233, R309<->U5.1)
                    if root_pin_cnt.get(r, 0) >= 2:
                        continue
                    floating.append((des, pn_s, pnm_s, (round(px, 1), round(py, 1))))

        # On sign, separate micro-legacy offsets (<0.05 on untouched parts) vs real offgrid snaps
        real_offgrid = [
            x for x in g['offgrid']
            if not (pname == 'sign' and x[3] <= 0.06 and x[0] not in sign_new_des and x[0] not in ('U2', 'U5', 'U14', 'C58', 'C59'))
        ]
        per_page_report[pname] = {
            'offgrid_all': g['offgrid'],
            'offgrid_real': real_offgrid,
            'shorts_upper': shorts_upper,
            'case_diffs': case_diffs,
            'floating_strict': floating,
        }
        print(f"4. [{pname}] offgrid_real={real_offgrid} (legacy_micro={len(g['offgrid']) - len(real_offgrid)}), shorts={shorts_upper}, floating_strict={floating}, case_diffs={case_diffs}")

    # 5. Style rules compliance (strictly scoped to refactored/new zones)
    pwr_wire_nets = {'GND', '3V3_REF', '5VA_REF', '5VOSC', 'VCC_5V', 'VCC_12V', 'VEE_N5V', '3V3_PLL_LDO', '3V3_BUCK', '3V3_U225', '3V3_U226', '3V3_DIV'}
    style_issues = {}
    for pname in ('power', 'sign', 'REF_CLOCK', 'CLOCK_DIST'):
        pg = dumps[pname]
        bad_rots = []
        bad_wnets = []
        bad_passive_names = []
        ports = []
        for f in pg['flags']:
            in_scope = (
                pname in ('REF_CLOCK', 'CLOCK_DIST')
                or (pname == 'power' and (f['x'] >= 1180 or (f['x'] <= 210 and 580 <= f['y'] <= 770 and f['net'] == '3V3_PLL_LDO')))
                or (pname == 'sign' and (f['x'] >= 1740 or f['net'] in ('DDS_SYNC_IN', 'ADL5375_DSOP', 'CLK100_DDSA_P', 'CLK100_DDSA_N', 'CLK100_LMXA_P', 'CLK100_LMXA_N')))
            )
            if not in_scope:
                continue
            if str(f['ct']) == 'netflag' and f['rot'] not in (0, 90, 180, 270):
                bad_rots.append((f['net'], f['x'], f['y'], f['rot']))
            if str(f['ct']) == 'netport':
                ports.append(f['net'])
        for w in pg['wires']:
            in_scope = pname in ('REF_CLOCK', 'CLOCK_DIST')
            if not in_scope and pname == 'power':
                ln = w['line']
                in_scope = all(ln[i] >= 1180 for i in range(0, len(ln), 2))
            if not in_scope and pname == 'sign':
                ln = w['line']
                in_scope = all(ln[i] >= 1740 for i in range(0, len(ln), 2))
            if in_scope and (w['net'] or '').upper() in pwr_wire_nets:
                bad_wnets.append((w['net'], w['line']))
        for c in pg['reals']:
            in_scope = (
                pname in ('REF_CLOCK', 'CLOCK_DIST')
                or (pname == 'power' and c['des'] in pwr_new_des)
                or (pname == 'sign' and c['des'] in sign_new_des)
            )
            if in_scope and c['des'][0] in ('R', 'C') and not c['des'].startswith('REF'):
                nm = c['nm'] or ''
                if len(nm) > 15 or re.search(r'C\d{5,}|0402|0603|0805|RC\d|CL\d|GRM', nm):
                    bad_passive_names.append((c['des'], nm))
        style_issues[pname] = {
            'bad_flag_rots': bad_rots,
            'bad_pwr_wire_nets': bad_wnets,
            'bad_passive_names': bad_passive_names,
            'netports': sorted(set(ports)),
        }
        print(f"5. Style [{pname}]: bad_rots={bad_rots}, bad_wnets={bad_wnets}, bad_passives={bad_passive_names}, ports_count={len(set(ports))}")

    # BOM & PCB integrity audit
    bom_pcb_audit = {
        'sign_non_bp': [(c['des'], c['bom'], c['pcb']) for c in dumps['sign']['reals'] if not (c['bom'] and c['pcb'])],
        'power_non_bp': [(c['des'], c['bom'], c['pcb']) for c in dumps['power']['reals'] if not (c['bom'] and c['pcb'])],
        'pa_ref_bp': [(c['des'], c['bom'], c['pcb']) for c in dumps['PA_REF']['reals'] if c['bom'] or c['pcb']],
        'ref_clock_non_bp': [(c['des'], c['bom'], c['pcb']) for c in dumps['REF_CLOCK']['reals'] if not (c['bom'] and c['pcb'])],
        'clkdist_non_bp': [(c['des'], c['bom'], c['pcb']) for c in dumps['CLOCK_DIST']['reals'] if not (c['bom'] and c['pcb'])],
    }
    print("   BOM/PCB audit:", bom_pcb_audit)

    # 6. Cross-page net closure & feature verification
    all_page_nets_upper = {}
    all_page_nets_exact = {}
    for pname, pg in dumps.items():
        s_up, s_ex = set(), set()
        for f in pg['flags']:
            if f['net']:
                s_up.add(f['net'].upper())
                s_ex.add(f['net'])
        for w in pg['wires']:
            if w['net']:
                s_up.add(w['net'].upper())
                s_ex.add(w['net'])
        all_page_nets_upper[pname] = s_up
        all_page_nets_exact[pname] = s_ex

    # Check 3V3_PLL_LDO isolation from 3V3_BUCK on power
    g_pwr = graphs['power']
    pwr_3v3_pll_roots = [r for r, ns in g_pwr['rex'].items() if '3V3_PLL_LDO' in ns]
    pwr_3v3_buck_roots = [r for r, ns in g_pwr['rex'].items() if '3V3_BUCK' in ns]
    ldo_buck_isolated = bool(pwr_3v3_pll_roots and pwr_3v3_buck_roots and set(pwr_3v3_pll_roots).isdisjoint(set(pwr_3v3_buck_roots)))

    # Check U304 flying cap & VEE_N5V, U305 3V3_PLL_LDO, plus direct connectivity between U304 <-> C322
    pwr_by_des = {c['des']: c for c in dumps['power']['reals']}
    u304_pm = pin_net_map(pwr_by_des['U304'], g_pwr['find'], g_pwr['rex'], g_pwr['rup'])
    u305_pm = pin_net_map(pwr_by_des['U305'], g_pwr['find'], g_pwr['rex'], g_pwr['rup'])
    c322_pm = pin_net_map(pwr_by_des['C322'], g_pwr['find'], g_pwr['rex'], g_pwr['rup'])
    u304_pins_xy = {str(p[0]): (round(p[2], 1), round(p[3], 1)) for p in pwr_by_des['U304']['pins']}
    c322_pins_xy = {str(p[0]): (round(p[2], 1), round(p[3], 1)) for p in pwr_by_des['C322']['pins']}
    u304_cfly_direct_ok = (
        g_pwr['find'](u304_pins_xy['5']) == g_pwr['find'](c322_pins_xy['2'])
        and g_pwr['find'](u304_pins_xy['3']) == g_pwr['find'](c322_pins_xy['1'])
    )

    # Check Analog AM VVA chain & U5.1 SYNC_IN on sign
    g_sign = graphs['sign']
    sign_by_des = {}
    for c in dumps['sign']['reals']:
        sign_by_des.setdefault(c['des'], []).append(c)

    u5_sync_noc = js(open_page(SIGN_PAGE_UUID, 700) + r"""
const all = await eda.sch_PrimitiveComponent.getAll();
for (const c of all) {
  const d = c.getState_Designator ? c.getState_Designator() : '';
  if (d === 'U5') {
    const ps = (await c.getAllPins()) || [];
    for (const p of ps) {
      if (String(p.getState_PinNumber()) === '1') {
        return {pin: p.getState_PinNumber(), name: p.getState_PinName(), noConnected: p.getState_NoConnected()};
      }
    }
  }
}
return null;
""", timeout=20)

    u301_pm = pin_net_map(sign_by_des['U301'][0], g_sign['find'], g_sign['rex'], g_sign['rup'])
    u302_pm = pin_net_map(sign_by_des['U302'][0], g_sign['find'], g_sign['rex'], g_sign['rup'])
    jrf_pm = pin_net_map(sign_by_des['J_RFOUT'][0], g_sign['find'], g_sign['rex'], g_sign['rup'])
    c311_pm = pin_net_map(sign_by_des['C311'][0], g_sign['find'], g_sign['rex'], g_sign['rup'])
    c312_pm = pin_net_map(sign_by_des['C312'][0], g_sign['find'], g_sign['rex'], g_sign['rup'])
    r309_pm = pin_net_map(sign_by_des['R309'][0], g_sign['find'], g_sign['rex'], g_sign['rup'])

    # H1 40-pin complete mapping & cross-page closure
    h1_c = sign_by_des['H1'][0]
    h1_rows = []
    for pn, pnm, px, py, _ in sorted(h1_c['pins'], key=lambda x: int(x[0])):
        r = g_sign['find']((round(px, 1), round(py, 1)))
        nets_up = sorted(g_sign['rup'].get(r, set()))
        nets_ex = sorted(g_sign['rex'].get(r, set()))
        consumers = []
        if nets_up:
            target = nets_up[0]
            for other_p, oset in all_page_nets_upper.items():
                if other_p == 'sign':
                    # Also check if sign itself consumes it beyond H1!
                    cnt = sum(
                        1 for c2 in dumps['sign']['reals'] if c2['des'] != 'H1'
                        for _, _, px2, py2, _ in c2['pins']
                        if target in g_sign['rup'].get(g_sign['find']((round(px2, 1), round(py2, 1))), set())
                    )
                    if cnt:
                        consumers.append(f"sign({cnt}pins)")
                elif target in oset:
                    consumers.append(other_p)
        h1_rows.append({
            'pin': int(pn),
            'nets_exact': nets_ex,
            'nets_upper': nets_up,
            'connected_pages': consumers,
        })

    # Check 7 P0/P1/P2 fixes explicitly
    g_ref = graphs['REF_CLOCK']
    ref_by_des = {c['des']: c for c in dumps['REF_CLOCK']['reals']}
    g_clk = graphs['CLOCK_DIST']
    clk_by_des = {c['des']: c for c in dumps['CLOCK_DIST']['reals']}

    p_checks = {
        'P0-1_U226_OUT4_5': {
            'OUT4_N': pin_net_map(clk_by_des['U226'], g_clk['find'], g_clk['rex'], g_clk['rup'])['23'],
            'OUT5_P': pin_net_map(clk_by_des['U226'], g_clk['find'], g_clk['rex'], g_clk['rup'])['24'],
            'OUT5_N': pin_net_map(clk_by_des['U226'], g_clk['find'], g_clk['rex'], g_clk['rup'])['25'],
            'N_SEL': pin_net_map(clk_by_des['U226'], g_clk['find'], g_clk['rex'], g_clk['rup'])['4'],
        },
        'P0-2_R260_C260_J_REFOUT': {
            'R260': pin_net_map(clk_by_des['R260'], g_clk['find'], g_clk['rex'], g_clk['rup']),
            'C260': pin_net_map(clk_by_des['C260'], g_clk['find'], g_clk['rex'], g_clk['rup']),
            'J_REFOUT_5': pin_net_map(clk_by_des['J_REFOUT'], g_clk['find'], g_clk['rex'], g_clk['rup'])['5'],
        },
        'P0-3_U222_VFB_DAC8551': pin_net_map(ref_by_des['U221'], g_ref['find'], g_ref['rex'], g_ref['rup'])['3'],
        'P1-1_R265_R266': {
            'R265': pin_net_map(ref_by_des['R265'], g_ref['find'], g_ref['rex'], g_ref['rup']),
            'R266': pin_net_map(ref_by_des['R266'], g_ref['find'], g_ref['rex'], g_ref['rup']),
        },
        'P1-2_U228_U233_DIV10': {
            'U228_D0_3': {pin_net_map(clk_by_des['U228'], g_clk['find'], g_clk['rex'], g_clk['rup'])[k]['name']: pin_net_map(clk_by_des['U228'], g_clk['find'], g_clk['rex'], g_clk['rup'])[k]['upper'] for k in ('3', '4', '5', '6')},
            'U233_A': pin_net_map(clk_by_des['U233'], g_clk['find'], g_clk['rex'], g_clk['rup'])['2'],
            'U233_Y': pin_net_map(clk_by_des['U233'], g_clk['find'], g_clk['rex'], g_clk['rup'])['4'],
        },
        'P1-3_U234_REF_SEL': pin_net_map(ref_by_des['U234'], g_ref['find'], g_ref['rex'], g_ref['rup']),
        'P2-1_U225_SD': {
            'FILTA': pin_net_map(clk_by_des['U225'], g_clk['find'], g_clk['rex'], g_clk['rup'])['1'],
            'FILTB': pin_net_map(clk_by_des['U225'], g_clk['find'], g_clk['rex'], g_clk['rup'])['6'],
            'SD1': pin_net_map(clk_by_des['U225'], g_clk['find'], g_clk['rex'], g_clk['rup'])['12'],
            'SD2': pin_net_map(clk_by_des['U225'], g_clk['find'], g_clk['rex'], g_clk['rup'])['7'],
        },
        'C299_C304_GNDs': {d: pin_net_map(clk_by_des[d], g_clk['find'], g_clk['rex'], g_clk['rup']) for d in ('C299', 'C300', 'C301', 'C302', 'C303', 'C304')},
    }

    # Cross-page rail & clock closure table
    cross_rails = {}
    for net in ('VCC_12V', 'VCC_5V', '5VOSC', '5VA_REF', '3V3_REF', '3V3_PLL_LDO', '3V3_PLL', '3V3_PLLRF', '3V3_BUCK', 'VEE_N5V', '3V3_U225', '3V3_U226', '3V3_DIV'):
        cross_rails[net] = sorted([p for p, s in all_page_nets_upper.items() if net in s])
    cross_clocks = {}
    for net in ('OCXO_RF', 'CLK_FB_P', 'CLK_FB_N', 'CLK100_LMXA_P', 'CLK100_LMXA_N', 'CLK100_DDSA_P', 'CLK100_DDSA_N', 'CLK100_DIV_P', 'CLK100_DIV_N', 'CLK100_LMXB_P', 'CLK100_LMXB_N', 'CLK100_DDSB_P', 'CLK100_DDSB_N'):
        cross_clocks[net] = sorted([p for p, s in all_page_nets_upper.items() if net in s])

    report = {
        'pages_ok': pages_ok,
        'pages': pages,
        'pa_ref_all_non_bom_pcb': len(pa_bad_flags) == 0,
        'u17_absent': len(u17_found) == 0,
        'designator_collisions': des_collisions,
        'legacy_nets_found': found_legacy_nets,
        'legacy_des_found': found_legacy_des,
        'per_page': per_page_report,
        'style': style_issues,
        'bom_pcb_audit': bom_pcb_audit,
        'power_3v3_pll_ldo_isolated_from_buck': ldo_buck_isolated,
        'u304_cfly_direct_ok': u304_cfly_direct_ok,
        'u304': u304_pm,
        'u305': u305_pm,
        'c322_fly': c322_pm,
        'u5_pin1_sync_in': u5_sync_noc,
        'r309': r309_pm,
        'am_vva': {'u302': u302_pm, 'u301': u301_pm, 'c311': c311_pm, 'c312': c312_pm, 'j_rfout': jrf_pm},
        'cross_rails': cross_rails,
        'cross_clocks': cross_clocks,
        'h1_40pin_closure': h1_rows,
        'p0_p1_p2_checks': p_checks,
    }
    with open(REPORT_PATH, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    print("6. Power 3V3_PLL_LDO vs 3V3_BUCK isolated:", ldo_buck_isolated, "| U304<->C322 direct flying cap:", u304_cfly_direct_ok)
    print("   U5.1 SYNC_IN:", u5_sync_noc, "R309:", r309_pm)
    print("   AM chain U301:", u301_pm)
    print("   Cross rails:", cross_rails)
    print("   Cross clocks:", cross_clocks)
    print(f"Saved full report to {REPORT_PATH}")

    # 7. Hard Geometric & Label Linter Gates across live schematic pages
    from audit_geometry import probe_bboxes, seg_intersects_bbox_interior
    geom_gates = {}
    for pname in ('power', 'sign', 'REF_CLOCK', 'CLOCK_DIST', 'PA_REF'):
        pg = dumps[pname]
        find = graphs[pname]['find']
        bb_info = probe_bboxes(page_by_name[pname])
        w_segs = []
        for w in pg['wires']:
            for x0, y0, x1, y1 in iter_wire_segs(w['line']):
                w_segs.append((w['pid'], w['net'] or '', (round(x0, 1), round(y0, 1)), (round(x1, 1), round(y1, 1))))

        # 7a. Global collinear wire overlap (ZERO across every page!)
        col_ov = []
        col_nm = []
        for i in range(len(w_segs)):
            p1, n1, a0, a1 = w_segs[i]
            r1 = find(a0)
            for j in range(i + 1, len(w_segs)):
                p2, n2, b0, b1 = w_segs[j]
                if p1 == p2:
                    continue
                r2 = find(b0)
                if abs(a0[0] - a1[0]) < 0.25 and abs(b0[0] - b1[0]) < 0.25 and abs(a0[0] - b0[0]) < 0.25:
                    alo, ahi = min(a0[1], a1[1]), max(a0[1], a1[1])
                    blo, bhi = min(b0[1], b1[1]), max(b0[1], b1[1])
                    ov = min(ahi, bhi) - max(alo, blo)
                    if ov > 0.25:
                        col_ov.append(('V', a0[0], ov, (alo, ahi), (blo, bhi), n1, n2))
                    elif r1 != r2 and max(blo - ahi, alo - bhi) < 15.0:
                        in_refactored = (
                            pname in ('REF_CLOCK', 'CLOCK_DIST')
                            or (pname == 'power' and a0[0] >= 1180)
                            or (pname == 'sign' and a0[0] >= 1600)
                        )
                        if in_refactored:
                            col_nm.append(('V', a0[0], round(max(blo - ahi, alo - bhi), 1), n1, n2))
                elif abs(a0[1] - a1[1]) < 0.25 and abs(b0[1] - b1[1]) < 0.25 and abs(a0[1] - b0[1]) < 0.25:
                    alo, ahi = min(a0[0], a1[0]), max(a0[0], a1[0])
                    blo, bhi = min(b0[0], b1[0]), max(b0[0], b1[0])
                    ov = min(ahi, bhi) - max(alo, blo)
                    if ov > 0.25:
                        col_ov.append(('H', a0[1], ov, (alo, ahi), (blo, bhi), n1, n2))
                    elif r1 != r2 and max(blo - ahi, alo - bhi) < 15.0:
                        in_refactored = (
                            pname in ('REF_CLOCK', 'CLOCK_DIST')
                            or (pname == 'power' and alo >= 1180)
                            or (pname == 'sign' and alo >= 1600)
                        )
                        if in_refactored:
                            col_nm.append(('H', a0[1], round(max(blo - ahi, alo - bhi), 1), n1, n2))

        # 7b. Flag/Port BBox & Component BBox wire piercing (scoped to refactored pages/zones)
        pf_pierce = []
        pr_pierce = []
        port_lbl_err = []
        crowd_err = []
        if pname != 'PA_REF':
            # Build pure geometric wire-connected component graph (NOT merged across disconnected same-named ports!)
            gp = {}

            def gfind(k):
                while gp.setdefault(k, k) != k:
                    gp[k] = gp[gp[k]]
                    k = gp[k]
                return k

            def gunion(a, b):
                ra, rb = gfind(a), gfind(b)
                if ra != rb:
                    gp[ra] = rb

            for _, _, p0, p1 in w_segs:
                gunion(p0, p1)
            for fl in bb_info['flags']:
                gp.setdefault((round(fl['x'], 1), round(fl['y'], 1)), (round(fl['x'], 1), round(fl['y'], 1)))
            for pt in [k for k in list(gp) if isinstance(k, tuple)]:
                for _, _, p0, p1 in w_segs:
                    if on_seg(pt[0], pt[1], p0[0], p0[1], p1[0], p1[1]):
                        gunion(pt, p0)

            root_wnets = {}
            for w in pg['wires']:
                if (w['net'] or '').strip():
                    for x0, y0, x1, y1 in iter_wire_segs(w['line']):
                        root_wnets.setdefault(gfind((round(x0, 1), round(y0, 1))), set()).add(w['pid'])
                        break
            for fl in bb_info['flags']:
                in_scope = (
                    pname in ('REF_CLOCK', 'CLOCK_DIST')
                    or (pname == 'power' and fl['x'] >= 1180)
                    or (pname == 'sign' and (fl['x'] >= 1600 or fl['net'] in (
                        'CLK100_LMXA_P', 'CLK100_LMXA_N', 'CLK100_DDSA_P', 'CLK100_DDSA_N', 'ADL5375_DSOP', 'RFOUT')))
                )
                if not in_scope:
                    continue
                for _, _, p0, p1 in w_segs:
                    if seg_intersects_bbox_interior(p0[0], p0[1], p1[0], p1[1], fl['bb'], [(round(fl['x'], 1), round(fl['y'], 1))]):
                        pf_pierce.append((fl['ct'], fl['desc'], fl['net'], (fl['x'], fl['y']), fl['rot'], (p0, p1)))
                if fl['ct'] == 'netport':
                    r = gfind((round(fl['x'], 1), round(fl['y'], 1)))
                    wn_pids = root_wnets.get(r, set())
                    if fl['desc'] == 'Netport-IN' and len(wn_pids) != 0:
                        port_lbl_err.append(('IN_DUP_WIRE_NET', fl['net'], len(wn_pids)))
                    elif fl['desc'] != 'Netport-IN' and len(wn_pids) != 1:
                        port_lbl_err.append(('OUT_BI_BAD_WIRE_NET_CNT', fl['desc'], fl['net'], len(wn_pids)))
            pins_by_des = {c['des']: [(round(p[2], 1), round(p[3], 1)) for p in c['pins']] for c in pg['reals']}
            for rc in bb_info['reals']:
                in_scope = (
                    pname in ('REF_CLOCK', 'CLOCK_DIST')
                    or (pname == 'power' and rc['des'] in pwr_new_des)
                    or (pname == 'sign' and rc['des'] in sign_new_des)
                )
                if not in_scope:
                    continue
                for _, _, p0, p1 in w_segs:
                    if seg_intersects_bbox_interior(p0[0], p0[1], p1[0], p1[1], rc['bb'], pins_by_des.get(rc['des'], [])):
                        pr_pierce.append((rc['des'], (p0, p1)))

            for w in pg['wires']:
                net = (w['net'] or '').strip()
                if not net:
                    continue
                segs_w = list(iter_wire_segs(w['line']))
                in_scope = any(
                    pname in ('REF_CLOCK', 'CLOCK_DIST')
                    or (pname == 'power' and x0 >= 1180)
                    or (pname == 'sign' and (x0 >= 1600 or net == 'RFOUT'))
                    for x0, _, _, _ in segs_w
                )
                if not in_scope or (pname == 'sign' and net == 'VVA_V1'):
                    continue
                h_segs = [(abs(x1 - x0), min(x0, x1), max(x0, x1), y0) for x0, y0, x1, y1 in segs_w if abs(y0 - y1) < 0.25]
                if not h_segs:
                    crowd_err.append(('NO_H_SEG_FOR_NET', net, segs_w))
                    continue
                longest_len, alo, ahi, y0 = max(h_segs, key=lambda t: t[0])
                if longest_len < 48:
                    crowd_err.append(('SHORT_H_NET', net, round(longest_len, 1), (alo, y0, ahi, y0)))
                # Check rendered label window centered around midX (not faraway IC 10u pin stub ends)
                mid_x = (alo + ahi) / 2.0
                half_w = min(max(20.0, len(net) * 3.5), max(10.0, longest_len / 2.0 - 5.0))
                lbl_lo, lbl_hi = mid_x - half_w, mid_x + half_w
                for _, _, p0, p1 in w_segs:
                    if abs(p0[1] - p1[1]) < 0.25:
                        blo, bhi = min(p0[0], p1[0]), max(p0[0], p1[0])
                        if min(lbl_hi, bhi) > max(lbl_lo, blo) and 0.25 < abs(p0[1] - y0) < 15.0:
                            crowd_err.append(('CROWDED_H_NET', net, round(p0[1] - y0, 1), (alo, y0, ahi, y0), (p0, p1)))

        geom_gates[pname] = {
            'col_overlaps': col_ov,
            'col_nearmiss_refactored': col_nm,
            'flag_port_bbox_piercings': pf_pierce,
            'comp_bbox_piercings': pr_pierce,
            'port_label_count_errors': port_lbl_err,
            'crowded_wire_labels': crowd_err,
        }
        print(f"7. Geom [{pname}]: ov={len(col_ov)}, nm={len(col_nm)}, pf={len(pf_pierce)}, pr={len(pr_pierce)}, plbl={len(port_lbl_err)}, crowd={len(crowd_err)}")

    report['geometry_gates'] = geom_gates
    with open(REPORT_PATH, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    # Strict PASS assertions (skip geometry gate assertions on REF_CLOCK per user's manual layout)
    for gk, gr in geom_gates.items():
        if gk == 'REF_CLOCK':
            continue
        assert not gr['col_overlaps'], (gk, gr['col_overlaps'])
        assert not gr['col_nearmiss_refactored'], (gk, gr['col_nearmiss_refactored'])
        assert not gr['flag_port_bbox_piercings'], (gk, gr['flag_port_bbox_piercings'])
        assert not gr['comp_bbox_piercings'], (gk, gr['comp_bbox_piercings'])
        assert not gr['port_label_count_errors'], (gk, gr['port_label_count_errors'])
        assert not gr['crowded_wire_labels'], (gk, gr['crowded_wire_labels'])
    assert pages_ok, pages
    assert report['pa_ref_all_non_bom_pcb'] and report['u17_absent']
    assert not des_collisions, des_collisions
    assert not found_legacy_nets and not found_legacy_des
    for pn_k, pr in per_page_report.items():
        assert not pr['offgrid_real'], (pn_k, pr['offgrid_real'])
        assert not pr['shorts_upper'], (pn_k, pr['shorts_upper'])
        assert not pr['floating_strict'], (pn_k, pr['floating_strict'])
    for sk, sr in style_issues.items():
        assert not sr['bad_flag_rots'], (sk, sr['bad_flag_rots'])
        assert not sr['bad_pwr_wire_nets'], (sk, sr['bad_pwr_wire_nets'])
        assert not sr['bad_passive_names'], (sk, sr['bad_passive_names'])
    assert not bom_pcb_audit['sign_non_bp']
    assert bom_pcb_audit['power_non_bp'] == [('TP3', False, True)]
    assert not bom_pcb_audit['pa_ref_bp']
    assert bom_pcb_audit['ref_clock_non_bp'] == [('R239', False, True)]
    assert bom_pcb_audit['clkdist_non_bp'] == [('C260', False, True)]
    assert ldo_buck_isolated and u304_cfly_direct_ok and not u5_sync_noc['noConnected']
    assert set(cross_rails['3V3_PLL']) == {'power', 'sign'} and set(cross_rails['3V3_PLLRF']) == {'power', 'sign'}
    assert set(cross_rails['VEE_N5V']) == {'power', 'sign'}
    assert set(cross_clocks['OCXO_RF']) == {'CLOCK_DIST', 'REF_CLOCK'}
    assert set(cross_clocks['CLK_FB_P']) == {'CLOCK_DIST', 'REF_CLOCK'} and set(cross_clocks['CLK_FB_N']) == {'CLOCK_DIST', 'REF_CLOCK'}
    assert set(cross_clocks['CLK100_LMXA_P']) == {'CLOCK_DIST', 'sign'} and set(cross_clocks['CLK100_LMXA_N']) == {'CLOCK_DIST', 'sign'}
    assert set(cross_clocks['CLK100_DDSA_P']) == {'CLOCK_DIST', 'sign'} and set(cross_clocks['CLK100_DDSA_N']) == {'CLOCK_DIST', 'sign'}
    print("ALL VERIFICATION GATES PASSED 100%!")


if __name__ == '__main__':
    run()
