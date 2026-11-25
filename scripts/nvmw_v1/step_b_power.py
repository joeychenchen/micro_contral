# -*- coding: utf-8 -*-
"""Step B (Idempotent & Batched): Finalize PA page name & complete 'power' page refactor."""
import json
import math
import sys

sys.path.insert(0, r'c:\Users\Jo1yc\Desktop\硕士课题\_agent_tmp')
from nvmw_lib import (
    DEVS, PA_PAGE_UUID, POWER_PAGE_UUID, dump_page, get_pages, js, open_page
)


def segs_from_line(line):
    out = []
    for i in range(0, len(line) - 3, 4):
        x0, y0, x1, y1 = [round(v, 3) for v in line[i:i + 4]]
        if abs(x0 - x1) < 1e-4 and abs(y0 - y1) < 1e-4:
            continue
        out.append([x0, y0, x1, y1])
    return out


def run():
    # Phase 1: Confirm stray P1 deleted and PA page exists ('PA_REF' / 'pa')
    pages = get_pages()
    for p in pages:
        if p['name'] == 'P1' and p['uuid'] != PA_PAGE_UUID:
            js(f"await eda.dmt_Schematic.deleteSchematicPage({json.dumps(p['uuid'])}); return 1;")
    pa_cur = [p for p in pages if p['uuid'] == PA_PAGE_UUID]
    if pa_cur and pa_cur[0]['name'] not in ('pa', 'PA_REF'):
        js(f"await eda.dmt_Schematic.modifySchematicPageName({json.dumps(PA_PAGE_UUID)}, 'PA_REF'); return 1;")
    print('PA page confirmed:', get_pages())

    # Phase 2: Check live 'power' page and apply only remaining cleanups
    pg = dump_page(POWER_PAGE_UUID)
    by_des = {c['des']: c for c in pg['reals']}
    print(f"Live power before remaining edits: reals={len(pg['reals'])}, flags={len(pg['flags'])}, wires={len(pg['wires'])}")

    del_comp_pids, del_wire_pids, create_flags, create_wires = [], [], [], []
    for f in pg['flags']:
        net = f.get('net')
        if net == 'AGND':
            del_comp_pids.append(f['pid'])
            create_flags.append({'kind': 'Ground', 'net': 'GND', 'x': f['x'], 'y': f['y'], 'rot': f['rot']})
        elif net == '5vpa':
            del_comp_pids.append(f['pid'])
            create_flags.append({'kind': 'Power', 'net': '5VA_REF', 'x': f['x'], 'y': f['y'], 'rot': f['rot']})
        elif net == '3V3osc':
            del_comp_pids.append(f['pid'])
            create_flags.append({'kind': 'Power', 'net': '3V3_REF', 'x': f['x'], 'y': f['y'], 'rot': f['rot']})
        elif net == '3v3_sw':
            del_comp_pids.append(f['pid'])
        elif net == 'GND' and abs(f['x'] - 115) < 2 and abs(f['y'] - 495) < 2:
            del_comp_pids.append(f['pid'])

    for w in pg['wires']:
        wnet = w.get('net') or ''
        if wnet in ('VCC_12v', 'vcc12'):
            del_wire_pids.append(w['pid'])
            for seg in segs_from_line(w['line']):
                create_wires.append({'line': seg, 'net': 'VCC_12V'})
        elif wnet == '3V3osc':
            del_wire_pids.append(w['pid'])
            for seg in segs_from_line(w['line']):
                create_wires.append({'line': seg, 'net': '3V3_REF'})

    for des in ('R62', 'C128', 'C129', 'L5', 'L4', 'L6', 'C27', 'C45', 'C47'):
        if des in by_des:
            del_comp_pids.append(by_des[des]['pid'])

    if del_comp_pids or del_wire_pids or create_flags or create_wires:
        js(open_page(POWER_PAGE_UUID, 600) + f"""
const dwp = {json.dumps(del_wire_pids)};
if (dwp.length) await eda.sch_PrimitiveWire.delete(dwp);
const dcp = {json.dumps(del_comp_pids)};
if (dcp.length) await eda.sch_PrimitiveComponent.delete(dcp);
for (const fl of {json.dumps(create_flags)}) {{
  await eda.sch_PrimitiveComponent.createNetFlag(fl.kind, fl.net, fl.x, fl.y, fl.rot, false);
}}
for (const wr of {json.dumps(create_wires)}) {{
  await eda.sch_PrimitiveWire.create(wr.line, wr.net || undefined);
}}
await new Promise(r => setTimeout(r, 250));
await eda.sch_Document.save();
return 1;
""", timeout=180)
        pg = dump_page(POWER_PAGE_UUID)
        by_des = {c['des']: c for c in pg['reals']}

    # Check if 3V3_PLL_LDO flags on R10/R13 need rot adjustment so they don't collide with x=215
    # Replace R10/R13 flags with clean rot=270/90 stub check; verify current wires
    repl_comps = [
        ('L5', DEVS['SWPA6045S680MT'], 685, 545, 270, '68uH (SWPA6045S680MT)'),
        ('L4', DEVS['SWPA4030S2R2MT'], 265, 695, 270, '2.2uH (SWPA4030S2R2MT)'),
        ('L6', DEVS['SWPA4030S150MT'], 380, 420, 0, '15uH (SWPA4030S150MT)'),
        ('C27', DEVS['C22U_0805'], 265, 760, 90, '22uF 0805'),
        ('C45', DEVS['JVJ35V470M10x10'], 605, 495, 0, '470uF 35V (JVJ35V470M10x10)'),
        ('C47', DEVS['RVT25V180M6X8'], 665, 510, 0, '180uF 25V (RVT25V180M6X8)'),
    ]
    new_comps = [
        ('U304', DEVS['TPS60403DBVR'], 640, 100, 0, 'TPS60403DBVR (-5V)'),
        ('C321', DEVS['C1U_0603'], 550, 100, 90, '1uF 0603'),
        ('C322', DEVS['C1U_0603'], 590, 155, 0, '1uF 0603'),
        ('C323', DEVS['C1U_0603'], 730, 100, 90, '1uF 0603'),
        ('U305', DEVS['TLV75733PDBVR'], 960, 100, 0, 'TLV75733PDBVR (1A 3V3)'),
        ('C324', DEVS['C10U_0603'], 880, 100, 90, '10uF 0603'),
        ('C325', DEVS['C10U_0603'], 1040, 100, 90, '10uF 0603'),
    ]

    for batch_name, batch_list in [('repl', repl_comps), ('new', new_comps)]:
        to_place = [
            {'des': d, 'lib': dev[0], 'uuid': dev[1], 'x': x, 'y': y, 'rot': rot, 'name': nm}
            for (d, dev, x, y, rot, nm) in batch_list
            if d not in by_des
        ]
        if not to_place:
            print(f"Batch {batch_name}: already present, skipping create.")
            continue
        print(f"Placing batch {batch_name} ({len(to_place)} comps)...")
        res = js(open_page(POWER_PAGE_UUID, 500) + f"""
const items = {json.dumps(to_place, ensure_ascii=False)};
const placed = [], failed = [];
for (const it of items) {{
  let c = null;
  try {{ c = await eda.sch_PrimitiveComponent.create({{libraryUuid: it.lib, uuid: it.uuid}}, it.x, it.y, undefined, it.rot, false, false, false); }} catch(e) {{}}
  if (!c) {{ failed.push(it.des); continue; }}
  const a = c.toAsync();
  a.setState_Designator(it.des);
  a.setState_Name(it.name);
  await a.done();
  placed.push(it.des);
}}
await new Promise(r => setTimeout(r, 250));
await eda.sch_Document.save();
return {{placed, failed}};
""", timeout=180)
        print(f"Batch {batch_name} result:", res)
        if res['failed']:
            raise RuntimeError(f"Power placement failed in {batch_name}: {res['failed']}")

    # Refresh live page dump to inspect exact placed pins!
    pg = dump_page(POWER_PAGE_UUID)
    by_des = {c['des']: c for c in pg['reals']}
    for k in ('L5', 'L4', 'L6', 'C27', 'C45', 'C47', 'U304', 'C321', 'C322', 'C323', 'U305', 'C324', 'C325'):
        print(f"  {k} @{by_des[k]['x']},{by_des[k]['y']} rot={by_des[k]['rot']}: {by_des[k]['pins']}")

    # Check if C45 or C47 pin names indicate '+' on the wrong side; rotate 180 if so
    fix_rots = []
    for cdes, target_plus_x in [('C45', 625), ('C47', 685)]:
        explicit_plus = [p for p in by_des[cdes]['pins'] if '+' in str(p[1])]
        if explicit_plus and abs(explicit_plus[0][2] - target_plus_x) > 5:
            fix_rots.append((cdes, by_des[cdes]['pid'], (by_des[cdes]['rot'] + 180) % 360))
    if fix_rots:
        print('Rotating electrolytic caps:', fix_rots)
        js(open_page(POWER_PAGE_UUID, 500) + f"""
for (const [des, pid, newRot] of {json.dumps(fix_rots)}) {{
  const c = await eda.sch_PrimitiveComponent.get(pid);
  if (c) {{ const a = c.toAsync(); a.setState_Rotation(newRot); await a.done(); }}
}}
await eda.sch_Document.save();
return 1;
""")
        pg = dump_page(POWER_PAGE_UUID)
        by_des = {c['des']: c for c in pg['reals']}

    # Helper to lookup pin coords from live dump
    def get_pin(des, match_names=None, num=None):
        for pn, pnm, px, py, _ in by_des[des]['pins']:
            if num is not None and str(pn) == str(num):
                return px, py
            if match_names:
                up = str(pnm).upper()
                for m in match_names:
                    if m.upper() in up:
                        return px, py
        raise KeyError(f"{des} match={match_names} num={num} in {by_des[des]['pins']}")

    # Phase 4: Wire U304 & U305 ONLY if no VEE_N5V flag exists yet (idempotent)
    has_vee = any(f.get('net') == 'VEE_N5V' for f in pg['flags'])
    if not has_vee:
        w4, f4 = [], []

        def stub_flag(px, py, dx, dy, kind, net):
            ex, ey = px + dx, py + dy
            w4.append({'line': [px, py, ex, ey], 'net': net})
            if kind == 'Ground':
                rot = 180 if dy < 0 else (0 if dy > 0 else (270 if dx < 0 else 90))
            else:
                rot = 0 if dy < 0 else (180 if dy > 0 else (90 if dx < 0 else 270))
            f4.append({'kind': kind, 'net': net, 'x': ex, 'y': ey, 'rot': rot})

        # --- U304 (TPS60403DBVR) ---
        u304_in = get_pin('U304', ['IN', 'VIN'])
        u304_out = get_pin('U304', ['OUT', 'VOUT'])
        u304_gnd = get_pin('U304', ['GND'])
        u304_cp = get_pin('U304', ['CFLY+', 'CAP+', 'C+'])
        u304_cm = get_pin('U304', ['CFLY-', 'CAP-', 'C-'])

        c321_1, c321_2 = get_pin('C321', num='1'), get_pin('C321', num='2')
        c321_t, c321_b = (c321_1, c321_2) if c321_1[1] < c321_2[1] else (c321_2, c321_1)
        stub_flag(c321_t[0], c321_t[1], 0, -15, 'Power', 'VCC_5V')
        stub_flag(c321_b[0], c321_b[1], 0, 15, 'Ground', 'GND')
        w4.append({'line': [u304_in[0], u304_in[1], c321_t[0], u304_in[1]], 'net': 'VCC_5V'})
        w4.append({'line': [c321_t[0], u304_in[1], c321_t[0], c321_t[1]], 'net': 'VCC_5V'})

        stub_flag(u304_gnd[0], u304_gnd[1], 0, -15 if u304_gnd[1] < by_des['U304']['y'] else 15, 'Ground', 'GND')

        c323_1, c323_2 = get_pin('C323', num='1'), get_pin('C323', num='2')
        c323_t, c323_b = (c323_1, c323_2) if c323_1[1] < c323_2[1] else (c323_2, c323_1)
        stub_flag(c323_t[0], c323_t[1], 0, -15, 'Power', 'VEE_N5V')
        stub_flag(c323_b[0], c323_b[1], 0, 15, 'Ground', 'GND')
        w4.append({'line': [u304_out[0], u304_out[1], c323_t[0], u304_out[1]], 'net': 'VEE_N5V'})
        w4.append({'line': [c323_t[0], u304_out[1], c323_t[0], c323_t[1]], 'net': 'VEE_N5V'})

        # Flying cap C322 connected cleanly via short net stubs (zero chance of crossing CFLY/IN/GND!)
        c322_1, c322_2 = get_pin('C322', num='1'), get_pin('C322', num='2')
        c322_l, c322_r = (c322_1, c322_2) if c322_1[0] < c322_2[0] else (c322_2, c322_1)
        # Check whether CFLY+ and CFLY- are on left side (x<640) or right side; direct Manhattan or net-named stubs
        stub_flag(u304_cp[0], u304_cp[1], -15 if u304_cp[0] < 640 else 15, 0, 'BI', 'CFLY_P')
        stub_flag(u304_cm[0], u304_cm[1], -15 if u304_cm[0] < 640 else 15, 0, 'BI', 'CFLY_M')
        stub_flag(c322_l[0], c322_l[1], -15, 0, 'BI', 'CFLY_P')
        stub_flag(c322_r[0], c322_r[1], 15, 0, 'BI', 'CFLY_M')

        # --- U305 (TLV75733PDBVR) ---
        u305_in = get_pin('U305', ['IN'])
        u305_en = get_pin('U305', ['EN'])
        u305_gnd = get_pin('U305', ['GND'])
        u305_out = get_pin('U305', ['OUT'])

        c324_1, c324_2 = get_pin('C324', num='1'), get_pin('C324', num='2')
        c324_t, c324_b = (c324_1, c324_2) if c324_1[1] < c324_2[1] else (c324_2, c324_1)
        stub_flag(c324_t[0], c324_t[1], 0, -15, 'Power', 'VCC_5V')
        stub_flag(c324_b[0], c324_b[1], 0, 15, 'Ground', 'GND')

        c325_1, c325_2 = get_pin('C325', num='1'), get_pin('C325', num='2')
        c325_t, c325_b = (c325_1, c325_2) if c325_1[1] < c325_2[1] else (c325_2, c325_1)
        stub_flag(c325_t[0], c325_t[1], 0, -15, 'Power', '3V3_PLL_LDO')
        stub_flag(c325_b[0], c325_b[1], 0, 15, 'Ground', 'GND')

        w4.append({'line': [u305_in[0], u305_in[1], c324_t[0], u305_in[1]], 'net': 'VCC_5V'})
        w4.append({'line': [c324_t[0], u305_in[1], c324_t[0], c324_t[1]], 'net': 'VCC_5V'})
        w4.append({'line': [u305_en[0], u305_en[1], c324_t[0], u305_en[1]], 'net': 'VCC_5V'})
        w4.append({'line': [c324_t[0], u305_en[1], c324_t[0], c324_t[1]], 'net': 'VCC_5V'})
        stub_flag(u305_gnd[0], u305_gnd[1], -15 if u305_gnd[0] < 960 else 15, 0, 'Ground', 'GND')
        w4.append({'line': [u305_out[0], u305_out[1], c325_t[0], u305_out[1]], 'net': '3V3_PLL_LDO'})
        w4.append({'line': [c325_t[0], u305_out[1], c325_t[0], c325_t[1]], 'net': '3V3_PLL_LDO'})

        # Deduplicate exact wire segments & filter zero-length
        seen_w = set()
        uniq_w4 = []
        for wr in w4:
            x0, y0, x1, y1 = [round(v, 3) for v in wr['line']]
            if abs(x0 - x1) < 1e-4 and abs(y0 - y1) < 1e-4:
                continue
            k = (min((x0, y0), (x1, y1)), max((x0, y0), (x1, y1)), wr['net'])
            if k not in seen_w:
                seen_w.add(k)
                uniq_w4.append({'line': [x0, y0, x1, y1], 'net': wr['net']})

        # Wait: split NetPorts (kind=='BI') from createNetFlag vs createNetPort!
        net_flags = [fl for fl in f4 if fl['kind'] in ('Power', 'Ground')]
        net_ports = [fl for fl in f4 if fl['kind'] not in ('Power', 'Ground')]

        js(open_page(POWER_PAGE_UUID, 500) + f"""
for (const fl of {json.dumps(net_flags)}) {{
  await eda.sch_PrimitiveComponent.createNetFlag(fl.kind, fl.net, fl.x, fl.y, fl.rot, false);
}}
for (const np of {json.dumps(net_ports)}) {{
  await eda.sch_PrimitiveComponent.createNetPort(np.kind, np.net, np.x, np.y, np.rot, false);
}}
for (const wr of {json.dumps(uniq_w4)}) {{
  await eda.sch_PrimitiveWire.create(wr.line, wr.net || undefined);
}}
await eda.sch_PrimitiveRectangle.create(490, 35, 620, 155, 8, 0, '#0055AA', 'none', 1, null, null);
await eda.sch_PrimitiveText.create(500, 28, '新增模拟负压(-5V电荷泵 U304) 与 LMX2595 专用线性LDO(U305 1A 3V3_PLL_LDO)', 0, '#0055AA', null, 13, true, false, false, 1);
await new Promise(r => setTimeout(r, 250));
await eda.sch_Document.save();
return 1;
""", timeout=180)

    # Read-back verification of power page
    pg_fin = dump_page(POWER_PAGE_UUID)
    bad_flags = [f['net'] for f in pg_fin['flags'] if f.get('net') in ('AGND', '5vpa', '3V3osc', '3v3_sw', 'VCC_12v', 'vcc12', 'amp_12V')]
    bad_wnets = [w['net'] for w in pg_fin['wires'] if w.get('net') in ('AGND', '5vpa', '3V3osc', '3v3_sw', 'VCC_12v', 'vcc12', 'amp_12V')]
    fin_des = {c['des'] for c in pg_fin['reals']}
    offgrid = []
    for c in pg_fin['reals']:
        for pn, pnm, px, py, _ in c['pins']:
            best = 999.0
            for w in pg_fin['wires']:
                ln = w['line']
                for i in range(0, len(ln), 2):
                    d = math.hypot(px - ln[i], py - ln[i + 1])
                    if d < best:
                        best = d
            if 0.02 < best < 5.0:
                offgrid.append((c['des'], pn, round(best, 3)))
    print(f"POWER VERIFY: reals={len(pg_fin['reals'])}, flags={len(pg_fin['flags'])}, wires={len(pg_fin['wires'])}, bad_flags={bad_flags}, bad_wnets={bad_wnets}, offgrid={offgrid}")
    print('Missing new/repl:', [d for d in ('L5','L4','L6','C27','C45','C47','U304','C321','C322','C323','U305','C324','C325') if d not in fin_des])


if __name__ == '__main__':
    run()
