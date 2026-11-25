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

    # 1. Clean out partial unsaved task-991 flags/ports & wires in x>1700 + LVDS/R309/DSOP/RFOUT ports
    temp_nets = {'CLK100_LMXA_P', 'CLK100_LMXA_N', 'CLK100_DDSA_P', 'CLK100_DDSA_N', 'ADL5375_DSOP', 'RFOUT', 'DDS_SYNC_IN'}
    del_flag_pids = []
    for f in pg['flags']:
        if f.get('ct') == 'sheet':
            continue
        if f['x'] > 1700 or f.get('net') in temp_nets or (f.get('net') == 'GND' and abs(f['x'] - 270) < 2 and abs(f['y'] - 500) < 6):
            del_flag_pids.append(f['pid'])

    del_wire_pids = []
    for w in pg['wires']:
        xs = w['line'][0::2]
        if max(xs) > 1700 or w.get('net') in temp_nets:
            del_wire_pids.append(w['pid'])
        elif any(abs(w['line'][i] - 270) < 2 and abs(w['line'][i + 1] - 520) < 2 for i in range(0, len(w['line']), 2)):
            del_wire_pids.append(w['pid'])

    meta = js(open_page(SIGN_PAGE_UUID, 500) + """
const rs = (await eda.sch_PrimitiveRectangle.getAll()) || [];
const ts = (await eda.sch_PrimitiveText.getAll()) || [];
return {
  rects: rs.map(r => ({pid: r.getState_PrimitiveId(), x: r.getState_TopLeftX()})),
  texts: ts.map(t => ({pid: t.getState_PrimitiveId(), x: t.getState_X()}))
};
""")
    del_rect_pids = [r['pid'] for r in meta['rects'] if r['x'] >= 1750]
    del_text_pids = [t['pid'] for t in meta['texts'] if t['x'] >= 1750]

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
        'C313': (1860, 500, 90), 'C314': (1905, 500, 90),
        'U302': (1995, 495, 0), 'R308': (2060, 425, 90),
        # Stage 2: OPA2192-A Inverter (V1)
        'R301': (2265, 425, 0),
        'R302': (2400, 505, 0), 'C316': (2400, 545, 0),
        'C315': (2510, 500, 90), 'C320': (2490, 355, 90),
        'R307': (2535, 415, 0), 'C318': (2590, 390, 90),
        # Stage 3: OPA2192-B V2 Servo + Clamp
        'R304': (2255, 240, 90), 'R303': (2255, 170, 90),
        'C317': (2390, 260, 0), 'R306': (2510, 195, 0),
        'C319': (2575, 165, 90), 'D301': (2655, 155, 0),
        'R305': (2705, 240, 90),
        # Stage 4: RF Path C311 -> U301 -> C312 -> J_RFOUT
        'C311': (2705, 335, 0), 'U301': (2820, 320, 0),
        'C312': (2925, 335, 0), 'J_RFOUT': (3020, 335, 180),
        # Stage 5: MCU Header H1
        'H1': (2050, 880, 0),
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
            'x': 2400,
            'y': 415 if is_a else 195,
            'rot': 0,
        })

    print(f"Cleaning temp items (flags={len(del_flag_pids)}, wires={len(del_wire_pids)}) & moving {len(updates)} sign parts...")
    js(open_page(SIGN_PAGE_UUID, 500) + f"""
if ({json.dumps(del_wire_pids)}.length) await eda.sch_PrimitiveWire.delete({json.dumps(del_wire_pids)});
if ({json.dumps(del_flag_pids)}.length) await eda.sch_PrimitiveComponent.delete({json.dumps(del_flag_pids)});
if ({json.dumps(del_rect_pids)}.length) await eda.sch_PrimitiveRectangle.delete({json.dumps(del_rect_pids)});
if ({json.dumps(del_text_pids)}.length) await eda.sch_PrimitiveText.delete({json.dumps(del_text_pids)});
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
    r310_t, r310_b = tb('R310')
    wires.extend([
        ([450, 125, 450, r310_t[1], r310_t[0], r310_t[1]], 'CLK100_LMXA_P'),
        ([r310_t[0], r310_t[1], 395, r310_t[1]], None),
        ([490, 105, 490, 85, r310_b[0], 85, r310_b[0], r310_b[1]], None),
        ([r310_b[0], 85, 395, 85], 'CLK100_LMXA_N'),
    ])
    ports.append(('IN', 'BI', 'CLK100_LMXA_P', 395, r310_t[1], 180))
    ports.append(('IN', 'BI', 'CLK100_LMXA_N', 395, 85, 180))

    # AD9958 LVDS (C59.1=245,550; C58.1=275,680; R300=210,615 -> 210,635 & 210,595)
    r300_t, r300_b = tb('R300')
    wires.extend([
        ([245, 550, 210, 550, 190, 550], 'CLK100_DDSA_P'),
        ([210, 550, r300_b[0], r300_b[1]], None),
        ([275, 680, 210, 680, 190, 680], 'CLK100_DDSA_N'),
        ([210, 680, r300_t[0], r300_t[1]], None),
    ])
    ports.append(('IN', 'BI', 'CLK100_DDSA_P', 190, 550, 180))
    ports.append(('IN', 'BI', 'CLK100_DDSA_N', 190, 680, 180))

    # U5.1 SYNC_IN R309 @(290,520) -> left GND pointing DOWN rot=0!
    r309_l, r309_r = lr('R309')
    wires.extend([
        ([r309_r[0], r309_r[1], 320, 520], 'DDS_SYNC_IN'),
        ([r309_l[0], r309_l[1], 270, 500], None),
    ])
    flags.append(('Ground', 'GND', 270, 500, 0))

    # U14.1 DSOP & U14.16 RFOUT
    wires.append(([1315, 355, 1375, 355], 'ADL5375_DSOP'))
    ports.append(('IN', 'BI', 'ADL5375_DSOP', 1315, 355, 180))
    wires.append(([1485, 275, 1510, 275], 'RFOUT'))
    ports.append(('OUT', 'BI', 'RFOUT', 1510, 275, 0))

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
        ([c313_t[0], c313_t[1], c313_t[0], 535, 1885, 535], None),
        ([c314_t[0], c314_t[1], c314_t[0], 535], None),
        ([1885, 535, 1885, 555], None),
        ([1885, 535, 1930, 535, 1930, u2_vdd[1], u2_vdd[0], u2_vdd[1]], None),
        ([1930, u2_vdd[1], 1930, u2_vref[1], u2_vref[0], u2_vref[1]], None),
        ([c313_b[0], c313_b[1], c313_b[0], 465, 1885, 465, c314_b[0], 465, c314_b[0], c314_b[1]], None),
        ([1885, 465, 1885, 450], None),
    ])
    flags.append(('Power', '5VA_REF', 1885, 555, 0))
    flags.append(('Ground', 'GND', 1885, 450, 0))

    # U302.GND -> UP over ports -> RIGHT -> DOWN to GND@(2220,520)
    wires.append(([u2_gnd[0], u2_gnd[1], 2065, u2_gnd[1], 2065, 540, 2220, 540, 2220, 520], None))
    flags.append(('Ground', 'GND', 2220, 520, 0))

    # Staggered SPI ports entering U302 + R308 pull-up to 3V3_REF (rot=0 UP)
    wires.extend([
        ([u2_din[0], u2_din[1], 2095, u2_din[1]], 'AM_DAC_DIN'),
        ([u2_sclk[0], u2_sclk[1], 2175, u2_sclk[1]], 'AM_DAC_SCLK'),
        ([u2_cs[0], u2_cs[1], r308_t[0], u2_cs[1]], None),
        ([r308_t[0], u2_cs[1], 2095, u2_cs[1]], 'AM_DAC_CS'),
        ([r308_t[0], r308_t[1], r308_t[0], u2_cs[1]], None),
        ([r308_b[0], r308_b[1], r308_b[0], 390, 2035, 390, 2035, 405], None),
    ])
    flags.append(('Power', '3V3_REF', 2035, 405, 0))
    ports.append(('IN', 'BI', 'AM_DAC_DIN', 2095, u2_din[1], 0))
    ports.append(('IN', 'BI', 'AM_DAC_SCLK', 2175, u2_sclk[1], 0))
    ports.append(('IN', 'BI', 'AM_DAC_CS', 2095, u2_cs[1], 0))

    # AM_DAC_OUT from U302 VOUT/VFB underneath U302 -> R301.1
    r301_l, r301_r = lr('R301')
    wires.extend([
        ([u2_vfb[0], u2_vfb[1], 1935, u2_vfb[1], 1935, u2_vout[1]], None),
        ([u2_vout[0], u2_vout[1], 1935, u2_vout[1], 1935, 375, r301_l[0], 375, r301_l[0], r301_l[1]], 'AM_DAC_OUT'),
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
        ([r301_r[0], r301_r[1], 2325, r301_r[1]], 'AM_INV_SUM'),
        ([2325, r301_r[1], u3a_inn[0], u3a_inn[1]], None),
        ([2325, r301_r[1], 2325, r302_l[1], r302_l[0], r302_l[1]], None),
        ([2325, r302_l[1], 2325, c316_l[1], c316_l[0], c316_l[1]], None),
        # VINA+ -> GND
        ([u3a_inp[0], u3a_inp[1], 2345, u3a_inp[1], 2345, 380], None),
        # VOUTA -> R307.left + R302.right + C316.right ('VVA_VCTL')
        ([u3a_out[0], u3a_out[1], 2465, u3a_out[1]], 'VVA_VCTL'),
        ([2465, u3a_out[1], r307_l[0], r307_l[1]], None),
        ([2465, u3a_out[1], 2465, r302_r[1], r302_r[0], r302_r[1]], None),
        ([2465, r302_r[1], 2465, c316_r[1], c316_r[0], c316_r[1]], None),
    ])
    flags.append(('Ground', 'GND', 2345, 380, 0))

    # U303.1 VDD + C315 (5VA_REF) & VSS + C320 (VEE_N5V)
    wires.extend([
        ([u3a_vdd[0], u3a_vdd[1], u3a_vdd[0], 470, 2480, 470, 2480, 540, c315_t[0], 540, c315_t[0], c315_t[1]], None),
        ([c315_t[0], 540, c315_t[0], 560], None),
        ([c315_b[0], c315_b[1], c315_b[0], 465], None),
        ([u3a_vss[0], u3a_vss[1], u3a_vss[0], 355, 2475, 355, 2475, 385, c320_t[0], 385], None),
        ([c320_t[0], c320_t[1], c320_t[0], 400], None),
        ([c320_b[0], c320_b[1], c320_b[0], 320], None),
    ])
    flags.append(('Power', '5VA_REF', c315_t[0], 560, 0))
    flags.append(('Ground', 'GND', c315_b[0], 465, 0))
    flags.append(('Power', 'VEE_N5V', c320_t[0], 400, 0))
    flags.append(('Ground', 'GND', c320_b[0], 320, 0))

    # VVA_V1: R307.right -> C318 -> straight right to x=2895 -> down to U301.6 (V1)
    u1_v1 = pxy('U301', name='V1')
    wires.extend([
        ([r307_r[0], r307_r[1], c318_t[0], r307_r[1]], 'VVA_V1'),
        ([c318_t[0], c318_t[1], c318_t[0], r307_r[1]], None),
        ([c318_b[0], c318_b[1], c318_b[0], 360], None),
        ([c318_t[0], r307_r[1], 2895, r307_r[1], 2895, u1_v1[1], u1_v1[0], u1_v1[1]], None),
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
        ([u3b_out[0], u3b_out[1], 2450, u3b_out[1]], 'VVA_V2_DRV'),
        ([2450, u3b_out[1], r306_l[0], r306_l[1]], None),
        ([2450, u3b_out[1], 2450, c317_r[1], c317_r[0], c317_r[1]], None),
    ])
    flags.append(('Power', '5VA_REF', r304_t[0], 275, 0))
    flags.append(('Ground', 'GND', r303_b[0], 135, 0))

    # VVA_V2: R306.right -> C319 -> D301.3 -> U301.3 (V2)
    wires.extend([
        ([r306_r[0], r306_r[1], c319_t[0], r306_r[1]], 'VVA_V2'),
        ([c319_t[0], c319_t[1], c319_t[0], r306_r[1]], None),
        ([c319_b[0], c319_b[1], c319_b[0], 135], None),
        ([c319_t[0], r306_r[1], d3[0], r306_r[1], 2755, r306_r[1], 2755, u1_v2[1], u1_v2[0], u1_v2[1]], None),
        ([d3[0], d3[1], d3[0], r306_r[1]], None),
        # D301.1 -> VEE_N5V (Power rot=0 UP!), D301.2 -> GND (rot=0 DOWN!)
        ([d1[0], d1[1], d1[0], 100, 2600, 100, 2600, 120], None),
        ([d2[0], d2[1], d2[0], 120], None),
    ])
    flags.append(('Ground', 'GND', c319_b[0], 135, 0))
    flags.append(('Power', 'VEE_N5V', 2600, 120, 0))
    flags.append(('Ground', 'GND', d2[0], 120, 0))

    # Sense arm: 5VA_REF -> R305 -> VVA_I -> U301.4 (I) AND back along y=110 to U303.2 VINB+
    wires.extend([
        ([r305_t[0], r305_t[1], r305_t[0], 275], None),
        ([r305_b[0], r305_b[1], 2770, r305_b[1], 2770, u1_i[1], u1_i[0], u1_i[1]], 'VVA_I'),
        ([r305_b[0], r305_b[1], r305_b[0], 115, 2325, 115, 2325, u3b_inp[1], u3b_inp[0], u3b_inp[1]], None),
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
        ([2650, c311_l[1], c311_l[0], c311_l[1]], 'RFOUT'),
        ([c311_r[0], c311_r[1], u1_rf1[0], u1_rf1[1]], 'VVA_RFIN'),
        ([u1_rf2[0], u1_rf2[1], c312_l[0], c312_l[1]], 'VVA_RFOUT'),
        ([c312_r[0], c312_r[1], j5[0], j5[1]], 'VVA_OUT'),
        # U301 GNDs -> pointing DOWN rot=0
        ([u1_gnd1[0], u1_gnd1[1], 2740, u1_gnd1[1], 2740, 270], None),
        ([u1_gnd2[0], u1_gnd2[1], 2875, u1_gnd2[1], 2875, 270], None),
        ([u1_ep[0], u1_ep[1], u1_ep[0], 270], None),
        # J_RFOUT shield GND 1..4 -> clean shared GND@(3010,275,rot=0)
        ([j1[0], j1[1], j1[0], 295, 3010, 295, j2[0], 295, j2[0], j2[1]], None),
        ([3010, 295, 3010, 275], None),
        ([j3[0], j3[1], j3[0], 375, j4[0], 375, j4[0], j4[1]], None),
        ([j4[0], 375, 3055, 375, 3055, 295, j1[0], 295], None),
    ])
    ports.append(('IN', 'BI', 'RFOUT', 2650, c311_l[1], 180))
    flags.append(('Ground', 'GND', 2740, 270, 0))
    flags.append(('Ground', 'GND', 2875, 270, 0))
    flags.append(('Ground', 'GND', u1_ep[0], 270, 0))
    flags.append(('Ground', 'GND', 3010, 275, 0))

    # --- C. H1 40-Pin MCU Header Staggered Horizontal Fanout + Shared Left/Right GND Buses ---
    h1_c = c_by('H1')
    left_gnds, right_gnds = [], []
    sig_l_idx = 0
    sig_r_idx = 0
    for pn, _, px, py, prot in sorted(h1_c['pins'], key=lambda q: int(q[0])):
        num = int(pn)
        px, py = round(px, 1), round(py, 1)
        net = H1_PINS[num]
        if int(round(prot)) % 360 == 180:  # LEFT side (odd pins)
            if net == 'GND':
                left_gnds.append((px, py))
            else:
                ex = 1930 if (sig_l_idx % 2 == 0) else 1815
                sig_l_idx += 1
                wires.append(([px, py, ex, py], net))
                ports.append(('BI', 'BI', net, ex, py, 180))
        else:  # RIGHT side (even pins)
            if net == 'GND':
                right_gnds.append((px, py))
            else:
                ex = 2170 if (sig_r_idx % 2 == 0) else 2285
                sig_r_idx += 1
                wires.append(([px, py, ex, py], net))
                ports.append(('BI', 'BI', net, ex, py, 0))

    # Left GND bus x=1760 broken cleanly at every pin Y so T-junctions bind in EasyEDA!
    lg_ys = sorted([y for _, y in left_gnds], reverse=True)
    for px, py in left_gnds:
        wires.append(([px, py, 1760, py], None))
    for i in range(len(lg_ys) - 1):
        wires.append(([1760, lg_ys[i], 1760, lg_ys[i + 1]], None))
    wires.append(([1760, lg_ys[-1], 1760, 760], None))
    flags.append(('Ground', 'GND', 1760, 760, 0))

    # Right GND bus x=2340 broken cleanly at every pin Y
    rg_ys = sorted([y for _, y in right_gnds], reverse=True)
    for px, py in right_gnds:
        wires.append(([px, py, 2340, py], None))
    for i in range(len(rg_ys) - 1):
        wires.append(([2340, rg_ys[i], 2340, rg_ys[i + 1]], None))
    wires.append(([2340, rg_ys[-1], 2340, 760], None))
    flags.append(('Ground', 'GND', 2340, 760, 0))

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

    # Apply in batches <= 35
    ops = [('flag', x) for x in flags] + [('port', x) for x in ports] + [('wire', x) for x in wires]
    for idx in range(0, len(ops), 35):
        chunk = ops[idx:idx + 35]
        cf = [x for t, x in chunk if t == 'flag']
        cp = [x for t, x in chunk if t == 'port']
        cw = [x for t, x in chunk if t == 'wire']
        print(f"  Sign wiring batch {idx // 35 + 1}/{(len(ops) + 34) // 35} ({len(chunk)} items)...")
        bres = js(open_page(SIGN_PAGE_UUID, 350) + f"""
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
            raise RuntimeError(f"Batch {idx // 35 + 1} errors: {bres}")

    # Boxes & Titles + Save
    js(open_page(SIGN_PAGE_UUID, 350) + """
await eda.sch_PrimitiveRectangle.create(1780, 620, 1340, 560, 0, 0, '#000000', 'none', 1, null, null);
await eda.sch_PrimitiveText.create(1800, 600, '模拟域 AM 压控衰减链路 (DAC8551 → OPA2192 负压反相/V2阻抗伺服 → HMC346AMS8GETR → SMA)', 0, '#000000', null, 14, true, false, false, 1);
await eda.sch_PrimitiveRectangle.create(1720, 1040, 680, 320, 0, 0, '#000000', 'none', 1, null, null);
await eda.sch_PrimitiveText.create(1740, 1020, 'STM32H743 主控 40P 排针接口 (H1)', 0, '#000000', null, 14, true, false, false, 1);
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
            fin_segs.append(([round(ln[i], 3), round(ln[i+1], 3), round(ln[i+2], 3), round(ln[i+3], 3)], w['net']))
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
