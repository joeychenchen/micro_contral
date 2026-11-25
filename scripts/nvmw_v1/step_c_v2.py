# -*- coding: utf-8 -*-
"""Step C-v2: Rebuild 'sign' page AM VVA (left-to-right full orthogonal flow), H1 (staggered), & LVDS."""
import json
import math
import sys

sys.path.insert(0, r'c:\Users\Jo1yc\Desktop\硕士课题\_agent_tmp')
from nvmw_lib import SIGN_PAGE_UUID, dump_page, js, open_page

H1_PINS = {
    1: 'GND', 2: 'PLL_SCK', 3: 'PLL_SDI', 4: 'CSB', 5: 'CE',
    6: 'MUXout', 7: 'GND', 8: 'DDS_SCLK', 9: 'CS_DDS', 10: 'IOupdate',
    11: 'DDSIO_0', 12: 'DDSIO_1', 13: 'GND', 14: 'DDSIO_2', 15: 'DDSIO_3',
    16: 'DDS_P0', 17: 'DDS_P1', 18: 'DDS_P2', 19: 'GND', 20: 'DDS_P3',
    21: 'dds_rst', 22: 'DDS_SYNC_clk', 23: 'GND', 24: 'ADL5375_DSOP', 25: 'AM_DAC_CS',
    26: 'AM_DAC_SCLK', 27: 'AM_DAC_DIN', 28: 'GND', 29: 'SPI_REF_SCK', 30: 'SPI_REF_MOSI',
    31: 'ADF_LE', 32: 'ADF_CE', 33: 'GND', 34: 'DAC_SYNC_N', 35: 'REF_SEL',
    36: 'REF_LOCK', 37: 'EXTREF_DET', 38: 'GND', 39: 'VC_MON', 40: 'GND',
}


def on_seg(px, py, x0, y0, x1, y1, tol=0.15):
    if abs(x0 - x1) < tol and abs(px - x0) < tol:
        return min(y0, y1) - tol <= py <= max(y0, y1) + tol
    if abs(y0 - y1) < tol and abs(py - y0) < tol:
        return min(x0, x1) - tol <= px <= max(x0, x1) + tol
    return False


def verify_wires_graph(reals, flags_list, ports_list, wires_list):
    """Exact EasyEDA vertex/T-junction connectivity solver."""
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
    for line, net in wires_list:
        for i in range(0, len(line) - 2, 2):
            p0 = (round(line[i], 1), round(line[i + 1], 1))
            p1 = (round(line[i + 2], 1), round(line[i + 3], 1))
            if p0 == p1:
                raise RuntimeError(f"Zero-length segment inside polyline: {line}")
            if abs(p0[0] - p1[0]) > 0.35 and abs(p0[1] - p1[1]) > 0.35:
                raise RuntimeError(f"Non-orthogonal segment inside polyline: {line}")
            segs.append((p0, p1))
            union(p0, p1)
            if net:
                union(p0, ('NET', net))
    for fl in flags_list:
        pt = (round(fl[2], 1), round(fl[3], 1))
        parent.setdefault(pt, pt)
        if fl[1]:
            union(pt, ('NET', fl[1]))
    for np in ports_list:
        pt = (round(np[3], 1), round(np[4], 1))
        parent.setdefault(pt, pt)
        if np[2]:
            union(pt, ('NET', np[2]))
    for c in reals:
        for _, _, px, py, _ in c['pins']:
            pt = (round(px, 1), round(py, 1))
            parent.setdefault(pt, pt)

    pts = [k for k in list(parent) if isinstance(k, tuple) and isinstance(k[0], (int, float))]
    for pt in pts:
        for p0, p1 in segs:
            if on_seg(pt[0], pt[1], p0[0], p0[1], p1[0], p1[1]):
                union(pt, p0)

    rnames = {}
    for k in list(parent):
        if isinstance(k, tuple) and k[0] == 'NET':
            rnames.setdefault(find(k), set()).add(k[1])
    return find, rnames


def run():
    pg = dump_page(SIGN_PAGE_UUID)
    by_des_all = {}
    for c in pg['reals']:
        by_des_all.setdefault(c['des'], []).append(c)

    # 1. Clean out refactored/touchpoint flags/ports & wires idempotently (by geometry + temp nets!)
    temp_nets = {'CLK100_LMXA_P', 'CLK100_LMXA_N', 'CLK100_DDSA_P', 'CLK100_DDSA_N', 'ADL5375_DSOP', 'RFOUT', 'DDS_SYNC_IN'}
    def should_del_flag(f):
        if f.get('ct') == 'sheet':
            return False
        return f['x'] >= 1520 or f.get('net') in temp_nets or (f.get('net') == 'GND' and abs(f['x'] - 270) < 2 and abs(f['y'] - 500) < 6)

    del_flag_pids = [f['pid'] for f in pg['flags'] if should_del_flag(f)]

    def should_del_wire(w):
        ln = w['line']
        if not ln:
            return False
        xs = ln[0::2]
        ys = ln[1::2]
        mnx, mxx = min(xs), max(xs)
        mny, mxy = min(ys), max(ys)
        in_r309 = (mnx >= 268 and mxx <= 322 and mny >= 498 and mxy <= 522)
        in_dds_lvds = (mnx >= 160 and mxx <= 277 and mny >= 548 and mxy <= 770 and (mnx < 220 or mxy > 685))
        in_pll_lvds = (mnx >= 390 and mxx <= 495 and mny >= -95 and mxy <= 140)
        in_iq_dsop = (mnx >= 1313 and mxx <= 1377 and mny >= 353 and mxy <= 357)
        in_iq_rfout = (mnx >= 1483 and mxx <= 1627 and mny >= 183 and mxy <= 277 and mny <= 190)
        return mxx >= 1520 or w.get('net') in temp_nets or in_r309 or in_dds_lvds or in_pll_lvds or in_iq_dsop or in_iq_rfout

    del_wire_pids = [w['pid'] for w in pg['wires'] if should_del_wire(w)]

    meta = js(open_page(SIGN_PAGE_UUID, 500) + """
const rs = (await eda.sch_PrimitiveRectangle.getAll()) || [];
const ts = (await eda.sch_PrimitiveText.getAll()) || [];
return {
  rects: rs.map(r => ({pid: r.getState_PrimitiveId(), x: r.getState_TopLeftX()})),
  texts: ts.map(t => ({pid: t.getState_PrimitiveId(), x: t.getState_X()}))
};
""")
    del_rect_pids = [r['pid'] for r in meta['rects'] if r['x'] >= 1520]
    del_text_pids = [t['pid'] for t in meta['texts'] if t['x'] >= 1520]

    # 2. Simplify display names & reposition AM VVA left-to-right + H1
    clean_names = {
        'R300': '100Ω', 'R310': '100Ω', 'R309': '10kΩ',
        'C311': '100pF', 'C312': '100pF', 'C316': '100pF', 'C318': '100pF', 'C319': '100pF',
        'C313': '100nF', 'C315': '100nF', 'C320': '100nF', 'C314': '1uF', 'C317': '1nF',
        'R301': '10kΩ', 'R302': '10kΩ', 'R304': '10kΩ', 'R305': '10kΩ', 'R308': '10kΩ',
        'R303': '510Ω', 'R306': '1kΩ', 'R307': '1kΩ',
        'U301': 'HMC346AMS8GETR', 'U302': 'DAC8551IDGKR',
        'D301': 'BAV99', 'J_RFOUT': 'SMA-KE-5', 'H1': 'STM32H7_2x20P',
    }
    am_moves = {
        # Stage 1: DAC8551
        'C313': (1840, 500, 90), 'C314': (1880, 500, 90),
        'U302': (1975, 495, 0), 'R308': (2060, 425, 90),
        # Stage 2: OPA2192-A Inverter (V1)
        'R301': (2225, 425, 0),
        'R302': (2405, 520, 0), 'C316': (2405, 565, 0),
        'C315': (2545, 500, 90), 'C320': (2515, 325, 90),
        'R307': (2575, 415, 0), 'C318': (2630, 390, 90),
        # Stage 3: OPA2192-B V2 Servo + Clamp
        'R304': (2255, 240, 90), 'R303': (2255, 170, 90),
        'C317': (2390, 260, 0), 'R306': (2550, 195, 0),
        'C319': (2610, 165, 90), 'D301': (2670, 155, 0),
        'R305': (2705, 240, 90),
        # Stage 4: RF Path C311 -> U301 -> C312 -> J_RFOUT
        'C311': (2705, 335, 0), 'U301': (2820, 320, 0),
        'C312': (2925, 335, 0), 'J_RFOUT': (3035, 335, 180),
        # Stage 5: MCU Header H1 (wide fanout box above AM zone)
        'H1': (2100, 1150, 0),
        'R300': (215, 615, 270),
        'R310': (425, 115, 270),
    }

    updates = []
    for des, nm in clean_names.items():
        if des in by_des_all:
            c = by_des_all[des][0]
            it = {'pid': c['pid'], 'name': nm}
            if des in am_moves:
                it['x'], it['y'], it['rot'] = am_moves[des]
            updates.append(it)
    # Multi-unit U303.1 & U303.2
    for c in by_des_all['U303']:
        is_a = any(p[0] == '1' for p in c['pins'])
        updates.append({
            'pid': c['pid'],
            'name': 'OPA2192IDR',
            'x': 2405,
            'y': 415 if is_a else 195,
            'rot': 0,
        })

    print(f"Cleaning temp items (flags={len(del_flag_pids)}, initial wires={len(del_wire_pids)}) & moving {len(updates)} sign parts...", flush=True)
    js(open_page(SIGN_PAGE_UUID, 900) + "return 1;", timeout=30)
    rem_wires = []
    for rnd in range(30):
        cur_ws = js("""
const ws = (await eda.sch_PrimitiveWire.getAll()) || [];
return ws.map(w => ({pid: w.getState_PrimitiveId(), net: w.getState_Net() || '', line: w.getState_Line()}));
""", timeout=25)
        rem_wires = [w['pid'] for w in cur_ws if should_del_wire(w)]
        batch = rem_wires[:4]
        if not batch:
            break
        print(f"  del wires round {rnd+1}: {len(batch)} wires (remaining={len(rem_wires)})", flush=True)
        js(f"""
for (const id of {json.dumps(batch)}) {{
  await Promise.race([eda.sch_PrimitiveWire.delete(id), new Promise(r => setTimeout(r, 1500))]);
  await new Promise(r => setTimeout(r, 30));
}}
return 1;
""", timeout=30)
    assert not rem_wires, f"Still {len(rem_wires)} target wires left after 30 rounds"

    rem_flags = []
    for rnd in range(25):
        cur_fs = js("""
const comps = (await eda.sch_PrimitiveComponent.getAll()) || [];
const out = [];
for (const c of comps) {
  let ct = null; try { ct = c.getState_ComponentType(); } catch(e){}
  let des = null; try { des = c.getState_Designator(); } catch(e){}
  if (des && String(ct) !== 'netflag' && String(ct) !== 'netport') continue;
  let net = null; try { net = c.getState_Net(); } catch(e){}
  out.push({pid: c.getState_PrimitiveId(), ct: String(ct), net: net || '', x: c.getState_X(), y: c.getState_Y()});
}
return out;
""", timeout=25)
        rem_flags = [f['pid'] for f in cur_fs if should_del_flag(f)]
        batch = rem_flags[:5]
        if not batch:
            break
        print(f"  del flags round {rnd+1}: {len(batch)} flags (remaining={len(rem_flags)})", flush=True)
        js(f"""
for (const id of {json.dumps(batch)}) {{
  await Promise.race([eda.sch_PrimitiveComponent.delete(id), new Promise(r => setTimeout(r, 1500))]);
  await new Promise(r => setTimeout(r, 30));
}}
return 1;
""", timeout=30)
    assert not rem_flags, f"Still {len(rem_flags)} target flags left after 25 rounds"

    for i in range(0, len(del_rect_pids), 10):
        js(f"""
for (const id of {json.dumps(del_rect_pids[i:i+10])}) {{
  const r = await eda.sch_PrimitiveRectangle.get(id);
  if (r) await Promise.race([eda.sch_PrimitiveRectangle.delete(id), new Promise(res => setTimeout(res, 1500))]);
}}
return 1;
""", timeout=45)
    for i in range(0, len(del_text_pids), 10):
        js(f"""
for (const id of {json.dumps(del_text_pids[i:i+10])}) {{
  const t = await eda.sch_PrimitiveText.get(id);
  if (t) await Promise.race([eda.sch_PrimitiveText.delete(id), new Promise(res => setTimeout(res, 1500))]);
}}
return 1;
""", timeout=45)
    js(f"""
for (const u of {json.dumps(updates)}) {{
  const c = await eda.sch_PrimitiveComponent.get(u.pid);
  if (!c) continue;
  const a = c.toAsync();
  a.setState_Name(u.name);
  if (u.x !== undefined) {{ a.setState_X(u.x); a.setState_Y(u.y); a.setState_Rotation(u.rot); }}
  await a.done();
}}
await new Promise(r => setTimeout(r, 250));
return 1;
""", timeout=180)

    # Read actual live pins after moving
    pg2 = dump_page(SIGN_PAGE_UUID)
    by2 = {}
    for c in pg2['reals']:
        by2.setdefault(c['des'], []).append(c)

    def c_by(des, unit=0):
        if des == 'U303':
            return next(c for c in by2['U303'] if any(p[0] == ('1' if unit == 0 else '5') for p in c['pins']))
        return by2[des][unit]

    def pxy(des, num=None, name=None, unit=0):
        for pn, pnm, px, py, _ in c_by(des, unit)['pins']:
            if num is not None and str(pn) == str(num):
                return round(px, 1), round(py, 1)
            if name is not None and str(pnm).upper() == name.upper():
                return round(px, 1), round(py, 1)
        raise KeyError((des, num, name, unit))

    def tb(des):
        p1, p2 = c_by(des)['pins'][0], c_by(des)['pins'][1]
        a, b = (round(p1[2], 1), round(p1[3], 1)), (round(p2[2], 1), round(p2[3], 1))
        return (a, b) if a[1] > b[1] else (b, a)

    def lr(des):
        p1, p2 = c_by(des)['pins'][0], c_by(des)['pins'][1]
        a, b = (round(p1[2], 1), round(p1[3], 1)), (round(p2[2], 1), round(p2[3], 1))
        return (a, b) if a[0] < b[0] else (b, a)

    # Build flags, ports, wires per strict user rules
    flags = []  # (kind, net, x, y, rot) - ALL Power/Ground rot=0!
    ports = []  # (dir, libKind_unused, net, x, y, rot) -> createNetPort(dir, net, x, y, rot)
    wires = []  # (line, net_or_None) - Power & GND wires ALWAYS net=None!

    # --- A. LVDS, SYNC_IN, DSOP, RFOUT on mid ---
    # LMX2595 LVDS (R18.1=450,125; R36.1=490,105; R310=425,115 -> 425,135 & 425,95)
    # Routed cleanly down into empty zone y=-55/-85 (wire from left -> IN port MUST use rot=180, wire net=None!)
    r310_t, r310_b = tb('R310')
    wires.extend([
        ([450, 125, 450, r310_t[1], 405, r310_t[1], 405, -85, 435, -85], None),
        ([490, 105, 490, 85, 425, 85, 425, -55, 435, -55], None),
        ([r310_b[0], r310_b[1], 425, 85], None),
    ])
    ports.append(('IN', 'BI', 'CLK100_LMXA_N', 435, -55, 180))
    ports.append(('IN', 'BI', 'CLK100_LMXA_P', 435, -85, 180))

    # AD9958 LVDS (C59.1=245,550; C58.1=275,680; R300=215,615 -> 215,635 & 215,595)
    # Route cleanly above U5.2/U5.1 (maxY=720.5) at y=765 & y=740, left IN ports rot=0, wire net=None!
    r300_t, r300_b = tb('R300')
    x_ddsa_p = r300_b[0] - 15 if r300_b[0] >= 215 else 200
    wires.extend([
        ([275, 680, r300_t[0], 680, r300_t[0], 765, 165, 765], None),
        ([r300_t[0], 680, r300_t[0], r300_t[1]], None),
        ([245, 550, x_ddsa_p, 550, x_ddsa_p, 740, 165, 740], None),
        ([r300_b[0], r300_b[1], r300_b[0], 550], None),
    ])
    ports.append(('IN', 'BI', 'CLK100_DDSA_P', 165, 740, 0))
    ports.append(('IN', 'BI', 'CLK100_DDSA_N', 165, 765, 0))

    # U5.1 SYNC_IN R309 @(290,520) -> wire net=None (avoid overlapping R309/U5.1 pin 1!) + GND pointing DOWN rot=0
    r309_l, r309_r = lr('R309')
    wires.extend([
        ([r309_r[0], r309_r[1], 320, 520], None),
        ([r309_l[0], r309_l[1], 270, 500], None),
    ])
    flags.append(('Ground', 'GND', 270, 500, 0))

    # U14.1 DSOP (left IN rot=0, wire net=None) & U14.16 RFOUT (routed cleanly at y=185 clear of x=1525 & C120!)
    wires.append(([1315, 355, 1375, 355], None))
    ports.append(('IN', 'BI', 'ADL5375_DSOP', 1315, 355, 0))
    wires.append(([1485, 275, 1505, 275, 1505, 185], None))
    wires.append(([1505, 185, 1625, 185], 'RFOUT'))
    ports.append(('OUT', 'BI', 'RFOUT', 1625, 185, 0))

    # --- B. Analog AM VVA Left-to-Right Signal Flow ---
    # Stage 1: U302 + C313 + C314 + R308
    c313_t, c313_b = tb('C313')
    c314_t, c314_b = tb('C314')
    u2_vdd, u2_vref = pxy('U302', name='VDD'), pxy('U302', name='VREF')
    u2_vfb, u2_vout = pxy('U302', name='VFB'), pxy('U302', name='VOUT')
    u2_cs, u2_sclk, u2_din, u2_gnd = pxy('U302', name='SYNC#'), pxy('U302', name='SCLK'), pxy('U302', name='DIN'), pxy('U302', name='GND')
    r308_t, r308_b = tb('R308')

    # 5VA_REF bus to C313/C314/U302 (all power wires net=None, Power rot=0 UP)
    wires.extend([
        ([c313_t[0], c313_t[1], c313_t[0], 535, 1865, 535], None),
        ([c314_t[0], c314_t[1], c314_t[0], 535], None),
        ([1865, 535, 1865, 555], None),
        ([1865, 535, 1910, 535, 1910, u2_vdd[1], u2_vdd[0], u2_vdd[1]], None),
        ([1910, u2_vdd[1], 1910, u2_vref[1], u2_vref[0], u2_vref[1]], None),
        ([c313_b[0], c313_b[1], c313_b[0], 465, 1865, 465, c314_b[0], 465, c314_b[0], c314_b[1]], None),
        ([1865, 465, 1865, 450], None),
    ])
    flags.append(('Power', '5VA_REF', 1865, 555, 0))
    flags.append(('Ground', 'GND', 1865, 450, 0))

    # U302.GND -> UP over ports -> RIGHT -> DOWN to GND@(2210,530)
    wires.append(([u2_gnd[0], u2_gnd[1], 2025, u2_gnd[1], 2025, 555, 2210, 555, 2210, 530], None))
    flags.append(('Ground', 'GND', 2210, 530, 0))

    # Staggered SPI ports fanned to >=25u vertical spacing (y=520 / 490 / 465), IN rot=180, wire net=None!
    wires.extend([
        ([u2_din[0], u2_din[1], u2_din[0] + 15, u2_din[1], u2_din[0] + 15, 520, 2100, 520], None),
        ([u2_sclk[0], u2_sclk[1], 2100, u2_sclk[1]], None),
        ([u2_cs[0], u2_cs[1], r308_t[0], u2_cs[1], r308_t[0], 465, 2100, 465], None),
        ([r308_t[0], r308_t[1], r308_t[0], 465], None),
        ([r308_b[0], r308_b[1], r308_b[0], 390, 2020, 390, 2020, 405], None),
    ])
    flags.append(('Power', '3V3_REF', 2020, 405, 0))
    ports.append(('IN', 'BI', 'AM_DAC_DIN', 2100, 520, 180))
    ports.append(('IN', 'BI', 'AM_DAC_SCLK', 2100, u2_sclk[1], 180))
    ports.append(('IN', 'BI', 'AM_DAC_CS', 2100, 465, 180))

    # AM_DAC_OUT from U302 VOUT/VFB underneath U302 -> R301.1
    r301_l, r301_r = lr('R301')
    wires.extend([
        ([u2_vfb[0], u2_vfb[1], 1915, u2_vfb[1], 1915, u2_vout[1]], None),
        ([u2_vout[0], u2_vout[1], 1915, u2_vout[1], 1915, 375], None),
        ([1915, 375, r301_l[0], 375], 'AM_DAC_OUT'),
        ([r301_l[0], 375, r301_l[0], r301_l[1]], None),
    ])

    # Stage 2: U303.1 Inverter (V1)
    u3a_inn, u3a_inp = pxy('U303', name='VINA-', unit=0), pxy('U303', name='VINA+', unit=0)
    u3a_out, u3a_vdd, u3a_vss = pxy('U303', name='VOUTA', unit=0), pxy('U303', name='VDD', unit=0), pxy('U303', name='VSS', unit=0)
    r302_l, r302_r = lr('R302')
    c316_l, c316_r = lr('C316')
    c315_t, c315_b = tb('C315')
    c320_t, c320_b = tb('C320')
    r307_l, r307_r = lr('R307')
    c318_t, c318_b = tb('C318')

    # AM_INV_SUM: R301.right -> U303A VINA- + R302.left + C316.left
    wires.extend([
        ([r301_r[0], r301_r[1], 2330, r301_r[1]], 'AM_INV_SUM'),
        ([2330, r301_r[1], u3a_inn[0], u3a_inn[1]], None),
        ([2330, r301_r[1], 2330, r302_l[1], r302_l[0], r302_l[1]], None),
        ([2330, r302_l[1], 2330, c316_l[1], c316_l[0], c316_l[1]], None),
        # VINA+ -> GND
        ([u3a_inp[0], u3a_inp[1], 2350, u3a_inp[1], 2350, 380], None),
        # VOUTA -> R307.left + R302.right + C316.right ('VVA_VCTL' on [2475..2555, 415] clear of feedback tap!)
        ([u3a_out[0], u3a_out[1], 2475, u3a_out[1]], None),
        ([2475, u3a_out[1], r307_l[0], r307_l[1]], 'VVA_VCTL'),
        ([2475, u3a_out[1], 2475, r302_r[1], r302_r[0], r302_r[1]], None),
        ([2475, r302_r[1], 2475, c316_r[1], c316_r[0], c316_r[1]], None),
    ])
    flags.append(('Ground', 'GND', 2350, 380, 0))

    # U303.1 VDD + C315 (5VA_REF) & VSS + C320 (VEE_N5V cleanly below y=415 VVA_VCTL!)
    wires.extend([
        ([u3a_vdd[0], u3a_vdd[1], u3a_vdd[0], 480, 2515, 480, 2515, 540, c315_t[0], 540, c315_t[0], c315_t[1]], None),
        ([c315_t[0], 540, c315_t[0], 560], None),
        ([c315_b[0], c315_b[1], c315_b[0], 465], None),
        ([u3a_vss[0], u3a_vss[1], u3a_vss[0], 345, c320_t[0], 345], None),
        ([c320_t[0], c320_t[1], c320_t[0], 360], None),
        ([c320_b[0], c320_b[1], c320_b[0], 290], None),
    ])
    flags.append(('Power', '5VA_REF', c315_t[0], 560, 0))
    flags.append(('Ground', 'GND', c315_b[0], 465, 0))
    flags.append(('Power', 'VEE_N5V', c320_t[0], 360, 0))
    flags.append(('Ground', 'GND', c320_b[0], 290, 0))

    # VVA_V1: R307.right -> C318 -> straight right to x=2895 -> down to U301.6 (V1)
    u1_v1 = pxy('U301', name='V1')
    wires.extend([
        ([r307_r[0], r307_r[1], c318_t[0], r307_r[1]], None),
        ([c318_t[0], c318_t[1], c318_t[0], r307_r[1]], None),
        ([c318_b[0], c318_b[1], c318_b[0], 360], None),
        ([c318_t[0], r307_r[1], 2895, r307_r[1]], 'VVA_V1'),
        ([2895, r307_r[1], 2895, u1_v1[1], u1_v1[0], u1_v1[1]], None),
    ])
    flags.append(('Ground', 'GND', c318_b[0], 360, 0))

    # Stage 3: U303.2 V2 Impedance-Matching Servo + D301
    r304_t, r304_b = tb('R304')
    r303_t, r303_b = tb('R303')
    u3b_inn, u3b_inp, u3b_out = pxy('U303', name='VINB-', unit=1), pxy('U303', name='VINB+', unit=1), pxy('U303', name='VOUTB', unit=1)
    c317_l, c317_r = lr('C317')
    r306_l, r306_r = lr('R306')
    c319_t, c319_b = tb('C319')
    d1, d2, d3 = pxy('D301', num='1'), pxy('D301', num='2'), pxy('D301', num='3')
    r305_t, r305_b = tb('R305')
    u1_v2, u1_i = pxy('U301', name='V2'), pxy('U301', name='I')

    # Reference arm 5VA_REF -> R304 -> V_REF_BR -> R303 -> GND & VINB- + C317
    wires.extend([
        ([r304_t[0], r304_t[1], r304_t[0], 275], None),
        ([r304_b[0], r304_b[1], r304_b[0], u3b_inn[1], r303_t[0], r303_t[1]], None),
        ([r303_b[0], r303_b[1], r303_b[0], 135], None),
        ([r304_b[0], u3b_inn[1], 2335, u3b_inn[1]], 'V_REF_BR'),
        ([2335, u3b_inn[1], u3b_inn[0], u3b_inn[1]], None),
        ([2335, u3b_inn[1], 2335, c317_l[1], c317_l[0], c317_l[1]], None),
        # VOUTB -> C317.right & R306.left ('VVA_V2_DRV')
        ([u3b_out[0], u3b_out[1], 2460, u3b_out[1]], None),
        ([2460, u3b_out[1], r306_l[0], r306_l[1]], 'VVA_V2_DRV'),
        ([2460, u3b_out[1], 2460, c317_r[1], c317_r[0], c317_r[1]], None),
    ])
    flags.append(('Power', '5VA_REF', r304_t[0], 275, 0))
    flags.append(('Ground', 'GND', r303_b[0], 135, 0))

    # VVA_V2: R306.right -> C319 -> D301.3 -> U301.3 (V2)
    wires.extend([
        ([r306_r[0], r306_r[1], c319_t[0], r306_r[1]], None),
        ([c319_t[0], c319_t[1], c319_t[0], r306_r[1]], None),
        ([c319_b[0], c319_b[1], c319_b[0], 135], None),
        ([c319_t[0], r306_r[1], d3[0], r306_r[1], 2755, r306_r[1]], 'VVA_V2'),
        ([2755, r306_r[1], 2755, u1_v2[1], u1_v2[0], u1_v2[1]], None),
        ([d3[0], d3[1], d3[0], r306_r[1]], None),
        # D301.1 -> VEE_N5V (Power rot=0 UP!), D301.2 -> GND (rot=0 DOWN!)
        ([d1[0], d1[1], d1[0], 100, 2635, 100, 2635, 120], None),
        ([d2[0], d2[1], d2[0], 120], None),
    ])
    flags.append(('Ground', 'GND', c319_b[0], 135, 0))
    flags.append(('Power', 'VEE_N5V', 2635, 120, 0))
    flags.append(('Ground', 'GND', d2[0], 120, 0))

    # Sense arm: 5VA_REF -> R305 -> VVA_I -> U301.4 (I) AND back along y=80 cleanly below D301 to U303.2 VINB+!
    wires.extend([
        ([r305_t[0], r305_t[1], r305_t[0], 275], None),
        ([r305_b[0], r305_b[1], 2775, r305_b[1]], 'VVA_I'),
        ([2775, r305_b[1], 2775, u1_i[1], u1_i[0], u1_i[1]], None),
        ([r305_b[0], r305_b[1], r305_b[0], 80, 2325, 80, 2325, u3b_inp[1], u3b_inp[0], u3b_inp[1]], None),
    ])
    flags.append(('Power', '5VA_REF', r305_t[0], 275, 0))

    # Stage 4: RF path RFOUT -> C311 -> U301.1(RF1) / U301.8(RF2) -> C312 -> J_RFOUT.5
    c311_l, c311_r = lr('C311')
    c312_l, c312_r = lr('C312')
    u1_rf1, u1_rf2 = pxy('U301', name='RF1'), pxy('U301', name='RF2')
    u1_gnd1, u1_gnd2, u1_ep = pxy('U301', num='2'), pxy('U301', num='7'), pxy('U301', num='9')
    j5 = pxy('J_RFOUT', num='5')
    j1, j2, j3, j4 = pxy('J_RFOUT', num='1'), pxy('J_RFOUT', num='2'), pxy('J_RFOUT', num='3'), pxy('J_RFOUT', num='4')

    wires.extend([
        ([2650, c311_l[1], c311_l[0], c311_l[1]], None),  # IN port carries RFOUT label
        ([c311_r[0], c311_r[1], u1_rf1[0], u1_rf1[1]], None),
        ([u1_rf2[0], u1_rf2[1], c312_l[0], c312_l[1]], None),
        ([c312_r[0], c312_r[1], j5[0], j5[1]], 'VVA_OUT'),
        # U301 GNDs -> pointing DOWN rot=0
        ([u1_gnd1[0], u1_gnd1[1], 2740, u1_gnd1[1], 2740, 270], None),
        ([u1_gnd2[0], u1_gnd2[1], 2875, u1_gnd2[1], 2875, 270], None),
        ([u1_ep[0], u1_ep[1], u1_ep[0], 270], None),
        # J_RFOUT shield GND 1..4 -> clear outside J_RFOUT BBox at x=3100!
        ([j1[0], j1[1], j1[0], 295, 3025, 295, j2[0], 295, j2[0], j2[1]], None),
        ([3025, 295, 3025, 275], None),
        ([j3[0], j3[1], j3[0], 375, j4[0], 375, j4[0], j4[1]], None),
        ([j4[0], 375, 3100, 375, 3100, 295, j1[0], 295], None),
    ])
    ports.append(('IN', 'BI', 'RFOUT', 2650, c311_l[1], 0))
    flags.append(('Ground', 'GND', 2740, 270, 0))
    flags.append(('Ground', 'GND', 2875, 270, 0))
    flags.append(('Ground', 'GND', u1_ep[0], 270, 0))
    flags.append(('Ground', 'GND', 3025, 275, 0))

    # --- C. H1 40-Pin MCU Header: 30-unit Vertical Staircase Fanout (ZERO overlap!) + Shared GND Buses ---
    # Strategy:
    # - GND pins connect horizontally only 15u to vertical GND bus right beside H1 (pin-15 left / pin+15 right), terminating at GND flags at bottom (clear below signals!).
    # - Signal pins split cleanly into UP-group (y_out >= y_pin) and DOWN-group (y_out < y_pin) so vertical stairs NEVER cross horizontal signals!
    # - y_out values are at 30-unit pitch ending in 0 (930, 960, ..., 1380), never collinear with pin Ys ending in 5!
    h1_c = c_by('H1')
    left_sigs, right_sigs = [], []
    left_gnds, right_gnds = [], []
    for pn, _, px, py, prot in sorted(h1_c['pins'], key=lambda q: int(q[0])):
        num = int(pn)
        px, py = round(px, 1), round(py, 1)
        net = H1_PINS[num]
        if int(round(prot)) % 360 == 180:
            if net == 'GND':
                left_gnds.append((px, py))
            else:
                left_sigs.append((net, px, py))
        else:
            if net == 'GND':
                right_gnds.append((px, py))
            else:
                right_sigs.append((net, px, py))

    def fanout_side(sigs, gnds, is_left):
        n = len(sigs)
        # Sort top-to-bottom (descending pin Y)
        sigs_desc = sorted(sigs, key=lambda s: -s[2])
        # Assign monotonic descending y_out centered around 1150, 30u pitch ending in 0!
        y_top = 1140 + (n // 2) * 30
        targets = [(net, px, py, y_top - idx * 30) for idx, (net, px, py) in enumerate(sigs_desc)]
        up_grp = [t for t in targets if t[3] >= t[2]]      # already top-to-bottom -> inner turns closest!
        dn_grp = sorted([t for t in targets if t[3] < t[2]], key=lambda t: t[2])  # bottom-to-top -> inner turns closest!
        pin_x = sigs_desc[0][1]
        sgn = -1 if is_left else 1
        gnd_x = pin_x + sgn * 15
        # Left/Right GND bus broken at every GND pin & ends at bottom flag below lowest signal!
        y_low_gnd = min(targets[-1][3], min(y for _, y in gnds)) - 35
        g_ys = sorted([y for _, y in gnds], reverse=True)
        for gpx, gpy in gnds:
            wires.append(([gpx, gpy, gnd_x, gpy], None))
        for i in range(len(g_ys) - 1):
            wires.append(([gnd_x, g_ys[i], gnd_x, g_ys[i + 1]], None))
        wires.append(([gnd_x, g_ys[-1], gnd_x, y_low_gnd], None))
        flags.append(('Ground', 'GND', gnd_x, y_low_gnd, 0))

        # Signal staircase turns start 35u outside H1 pins, step 15u per track, outer port stub >=190u so label always centers on 30u-spaced outer stub!
        max_k = max(len(up_grp), len(dn_grp))
        port_x = pin_x + sgn * (35 + max_k * 15 + 190)
        for grp in (up_grp, dn_grp):
            for k, (net, px, py, yout) in enumerate(grp):
                tx = pin_x + sgn * (35 + k * 15)
                wires.append(([px, py, tx, py, tx, yout], None))
                wires.append(([tx, yout, port_x, yout], net))
                ports.append(('BI', 'BI', net, port_x, yout, 180 if is_left else 0))

    fanout_side(left_sigs, left_gnds, True)
    fanout_side(right_sigs, right_gnds, False)

    # --- Pre-flight verification BEFORE sending to EasyEDA! ---
    bad_rots = [fl for fl in flags if fl[4] != 0]
    if bad_rots:
        raise RuntimeError(f"Non-zero rot flags found: {bad_rots}")
    find_v, rnames_v = verify_wires_graph(pg2['reals'], flags, ports, wires)
    shorts = []
    for c in pg2['reals']:
        if c['des'] in clean_names or c['des'] == 'U303':
            for pn, pnm, px, py, _ in c['pins']:
                ns = rnames_v.get(find_v((round(px, 1), round(py, 1))), set())
                if len(ns) > 1:
                    shorts.append((c['des'], pn, pnm, sorted(ns)))
    if shorts:
        raise RuntimeError(f"PREFLIGHT SHORTS DETECTED: {shorts}")
    # Check key AM & H1 nets closed properly
    must_pairs = [
        ('U302.4->R301_l', pxy('U302', num='4'), r301_l),
        ('R301_r->U303.2', r301_r, u3a_inn),
        ('U303.1->R307_l', u3a_out, r307_l),
        ('R307_r->U301.6', r307_r, u1_v1),
        ('R304_b->U303.6', r304_b, u3b_inn),
        ('U303.7->R306_l', u3b_out, r306_l),
        ('R306_r->U301.3', r306_r, u1_v2),
        ('R306_r->D301.3', r306_r, d3),
        ('R305_b->U301.4', r305_b, u1_i),
        ('R305_b->U303.5', r305_b, u3b_inp),
        ('C311_r->U301.1', c311_r, u1_rf1),
        ('U301.8->C312_l', u1_rf2, c312_l),
        ('C312_r->J_RFOUT.5', c312_r, j5),
    ]
    for label, xy1, xy2 in must_pairs:
        if find_v(xy1) != find_v(xy2):
            raise RuntimeError(f"PREFLIGHT OPEN NET {label}: {rnames_v.get(find_v(xy1))} vs {rnames_v.get(find_v(xy2))}")
    print(f"PREFLIGHT PASSED 100%! wires={len(wires)}, flags={len(flags)}, ports={len(ports)}, shorts=0, AM links=OK")

    # Apply in batches <= 20 (avoid 60s bridge timeout!)
    ops = [('flag', x) for x in flags] + [('port', x) for x in ports] + [('wire', x) for x in wires]
    for idx in range(0, len(ops), 20):
        chunk = ops[idx:idx + 20]
        cf = [x for t, x in chunk if t == 'flag']
        cp = [x for t, x in chunk if t == 'port']
        cw = [x for t, x in chunk if t == 'wire']
        print(f"  Sign wiring batch {idx // 20 + 1}/{(len(ops) + 19) // 20} ({len(chunk)} items)...")
        bres = js(f"""
const errs = [];
for (const [kind, net, x, y, rot] of {json.dumps(cf)}) {{
  try {{ await eda.sch_PrimitiveComponent.createNetFlag(kind, net, x, y, rot, false); }}
  catch (e) {{ errs.push(['flag', kind, net, x, y, String(e)]); }}
}}
for (const [dir, _unused, net, x, y, rot] of {json.dumps(cp)}) {{
  try {{ await eda.sch_PrimitiveComponent.createNetPort(dir, net, x, y, rot, false); }}
  catch (e) {{ errs.push(['port', dir, net, x, y, String(e)]); }}
}}
for (const [line, net] of {json.dumps(cw)}) {{
  try {{
    const w = await (net ? eda.sch_PrimitiveWire.create(line, net) : eda.sch_PrimitiveWire.create(line));
    if (!w) errs.push(['wire_null', line, net]);
  }} catch (e) {{ errs.push(['wire_err', line, net, String(e)]); }}
}}
await new Promise(r => setTimeout(r, 150));
return errs;
""", timeout=180)
        if bres:
            raise RuntimeError(f"Batch {idx // 20 + 1} errors: {bres}")

    # Boxes & Titles + Save
    js(open_page(SIGN_PAGE_UUID, 350) + """
await eda.sch_PrimitiveRectangle.create(1760, 645, 1390, 595, 0, 0, '#000000', 'none', 1, null, null);
await eda.sch_PrimitiveText.create(1780, 625, '模拟域 AM 压控衰减链路 (DAC8551 → OPA2192 负压反相/V2阻抗伺服 → HMC346AMS8GETR → SMA)', 0, '#000000', null, 14, true, false, false, 1);
await eda.sch_PrimitiveRectangle.create(1540, 1490, 1120, 660, 0, 0, '#000000', 'none', 1, null, null);
await eda.sch_PrimitiveText.create(1560, 1470, 'STM32H743 主控 40P 排针接口 (H1)', 0, '#000000', null, 14, true, false, false, 1);
await new Promise(r => setTimeout(r, 250));
await eda.sch_Document.save();
return 1;
""")

    # Live read-back check (EasyEDA stores wire lines in 4-number [x0,y0,x1,y1] chunks)
    pg_fin = dump_page(SIGN_PAGE_UUID)
    fin_segs = []
    for w in pg_fin['wires']:
        ln = w['line']
        for i in range(0, len(ln) - 3, 4):
            seg = [round(ln[i], 3), round(ln[i+1], 3), round(ln[i+2], 3), round(ln[i+3], 3)]
            if (round(seg[0], 1), round(seg[1], 1)) != (round(seg[2], 1), round(seg[3], 1)):
                fin_segs.append((seg, w['net']))
    f_fin, rn_fin = verify_wires_graph(
        pg_fin['reals'],
        [(f['ct'], f['net'], f['x'], f['y'], f['rot']) for f in pg_fin['flags']],
        [],
        fin_segs,
    )
    shorts_live = []
    offgrid = []
    for c in pg_fin['reals']:
        for pn, pnm, px, py, _ in c['pins']:
            ns = rn_fin.get(f_fin((round(px, 1), round(py, 1))), set())
            if len(ns) > 1:
                shorts_live.append((c['des'], pn, pnm, sorted(ns)))
            best = 999.0
            for w in pg_fin['wires']:
                ln = w['line']
                for i in range(0, len(ln), 2):
                    d = math.hypot(px - ln[i], py - ln[i + 1])
                    if d < best:
                        best = d
            if 0.02 < best < 5.0:
                offgrid.append((c['des'], pn, round(best, 3)))
    bad_rots_live = [(f['net'], f['x'], f['y'], f['rot']) for f in pg_fin['flags'] if f['x'] > 1700 and f.get('ct') == 'netflag' and f['rot'] != 0]
    print(f"SIGN FINAL VERIFY: reals={len(pg_fin['reals'])}, flags={len(pg_fin['flags'])}, wires={len(pg_fin['wires'])}")
    print(f"  live_shorts={shorts_live}, offgrid={offgrid}, bad_rots_in_new_zone={bad_rots_live}")


if __name__ == '__main__':
    run()
