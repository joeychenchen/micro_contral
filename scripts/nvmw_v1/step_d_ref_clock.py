# -*- coding: utf-8 -*-
"""Step D1: Create & populate 'REF_CLOCK' page in NVmw (+200 offset, P1-1 & P1-3 fixes, no LDO Box 4, no J_H1)."""
import json
import math
import sys

sys.path.insert(0, r'c:\Users\Jo1yc\Desktop\硕士课题\_agent_tmp')
from nvmw_lib import DEVS, SCHEMATIC_UUID, dump_page, get_pages, js, open_page

PAGE_NAME = 'REF_CLOCK'


def on_seg(px, py, x0, y0, x1, y1, tol=0.15):
    if abs(x0 - x1) < tol and abs(px - x0) < tol:
        return min(y0, y1) - tol <= py <= max(y0, y1) + tol
    if abs(y0 - y1) < tol and abs(py - y0) < tol:
        return min(x0, x1) - tol <= px <= max(x0, x1) + tol
    return False


def verify_graph(reals, flags_list, ports_list, wires_list):
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
                continue
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
        pt = (round(np[2], 1), round(np[3], 1))
        parent.setdefault(pt, pt)
        if np[1]:
            union(pt, ('NET', np[1]))
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
    # 1. Create clean REF_CLOCK page (or resume existing if --resume passed)
    page_uuid = None
    for p in get_pages():
        if p['name'] == PAGE_NAME:
            if '--resume' in sys.argv:
                page_uuid = p['uuid']
            else:
                print(f"Deleting existing {PAGE_NAME} page {p['uuid']}...")
                js(f"await eda.dmt_Schematic.deleteSchematicPage({json.dumps(p['uuid'])}); await new Promise(r=>setTimeout(r,1000)); return 1;")

    if not page_uuid:
        page_uuid = js(f"return await eda.dmt_Schematic.createSchematicPage({json.dumps(SCHEMATIC_UUID)});")
        if not page_uuid:
            raise RuntimeError("createSchematicPage failed for REF_CLOCK")
        js(open_page(page_uuid, 900) + f"await eda.dmt_Schematic.modifySchematicPageName({json.dumps(page_uuid)}, {json.dumps(PAGE_NAME)}); await new Promise(r=>setTimeout(r,300)); return 1;")
    else:
        js(open_page(page_uuid, 600) + "return 1;")
    print(f"Active '{PAGE_NAME}' page: {page_uuid}")

    existing_pg = dump_page(page_uuid)
    existing_des = {c['des'] for c in existing_pg['reals']}
    existing_u222 = sum(1 for c in existing_pg['reals'] if c['des'] == 'U222')

    # 2. Define all 60 instances (Box 1..3 + [P1-1] R265/R266 + [P1-3] U234/C290 + shifted Box 4 Status LEDs dx=-1880)
    # tuple: (des, dev_key, fb_key_or_None, x, y, rot, display_name, bom, pcb, subPartName)
    DX_LED = -1880
    specs = [
        # Box 1: External 10MHz Input & Detect + P1-1 Bias
        ('J_REFIN', 'HL2_BNC_50KE', None, 200, 2215, 0, 'HL2-BNC-50KE', True, True, None),
        ('D202', 'PESD5V0S1BB', 'ESD5Z5V0C', 310, 2145, 270, 'PESD5V0S1BB', True, True, None),
        ('R240', 'R49R9_0402', None, 390, 2155, 270, '49.9Ω', True, True, None),
        ('C240', 'C100N_0402', None, 490, 2215, 0, '100nF', True, True, None),
        ('D201', 'BAV99', None, 600, 2145, 0, 'BAV99', True, True, None),
        ('R265', 'R10K_0402_V2', 'R10K_0402', 655, 2260, 270, '10kΩ', True, True, None),
        ('R266', 'R10K_0402_V2', 'R10K_0402', 665, 2170, 270, '10kΩ', True, True, None),
        ('R241', 'R100R_0402_V2', 'R100R_0402', 720, 2215, 0, '100Ω', True, True, None),
        ('C241', 'C100N_0402', None, 455, 1990, 0, '100nF', True, True, None),
        ('R242', 'R10K_0402_V2', 'R10K_0402', 580, 2035, 270, '10kΩ', True, True, None),
        ('R243', 'R10K_0402_V2', 'R10K_0402', 580, 1945, 270, '10kΩ', True, True, None),
        ('U224', 'SN74LVC1G14', '74LVC1G14GW', 700, 1980, 0, 'SN74LVC1G14', True, True, None),
        ('C242', 'C100N_0402', None, 890, 1950, 270, '100nF', True, True, None),

        # ADF4002 + Loop Filter (C246/C245/R245 raised above y=2215 so ADF_REFIN runs straight horizontal!)
        ('R245', 'R100R_0402_V2', 'R100R_0402', 875, 2270, 90, '100Ω', True, True, None),
        ('C246', 'C100P_0402', None, 925, 2295, 0, '100pF', True, True, None),
        ('C245', 'C100P_0402', None, 925, 2245, 0, '100pF', True, True, None),
        ('R246', 'R5K1_0402', None, 910, 2335, 180, '5.1kΩ', True, True, None),
        ('U220', 'ADF4002BRUZ', None, 1080, 2250, 0, 'ADF4002BRUZ', True, True, None),
        ('R249', 'R10K_0402_V2', 'R10K_0402', 1280, 2335, 270, '10kΩ', True, True, None),
        ('R244', 'R10K_0402_V2', 'R10K_0402', 1280, 2125, 270, '10kΩ', True, True, None),
        ('C270', 'C100N_0402', None, 1020, 1950, 270, '100nF', True, True, None),
        ('C271', 'C10N_0402', None, 1090, 1950, 0, '10nF', True, True, None),
        ('C272', 'C100N_0402', None, 1160, 1950, 270, '100nF', True, True, None),
        ('C273', 'C10N_0402', None, 1230, 1950, 0, '10nF', True, True, None),
        ('C274', 'C100N_0402', None, 1350, 1950, 270, '100nF', True, True, None),
        ('C275', 'C1U_0603_TDK', 'C1U_0603', 1420, 1950, 90, '1uF', True, True, None),
        ('C247', 'C330N_1210', None, 1540, 2290, 270, '330nF', True, True, None),
        ('R247', 'R22K_0402', None, 1640, 2320, 270, '22kΩ', True, True, None),
        ('C248', 'C2U2_FILM', 'C2U2_1210', 1640, 2215, 270, '2.2uF(Film)', True, True, None),
        ('R248', 'R10K_0402_V2', 'R10K_0402', 1720, 2380, 0, '10kΩ', True, True, None),
        ('C249', 'C22N_C0G', 'C22N_0402', 1820, 2290, 270, '22nF(C0G)', True, True, None),

        # Box 2: Vref Buffer (U222.1) + Calibration DAC (U221)
        ('U222', 'OPA2192IDR', None, 420, 1560, 0, 'OPA2192IDR', True, True, 'OPA2192IDR.1'),
        ('C251', 'C100N_0402', None, 580, 1500, 270, '100nF', True, True, None),
        ('U221', 'DAC8551IDGKR', None, 760, 1555, 0, 'DAC8551IDGKR', True, True, None),
        ('R256', 'R10K_0402_V2', 'R10K_0402', 880, 1460, 180, '10kΩ', True, True, None),
        ('R250', 'R10K_0402_V2', 'R10K_0402', 1120, 1440, 0, '10kΩ', True, True, None),
        ('C250', 'C10U_X7R', 'C10U_1206', 1220, 1385, 270, '10uF', True, True, None),
        ('C276', 'C100N_0402', None, 380, 1260, 270, '100nF', True, True, None),
        ('C277', 'C1U_0603_TDK', 'C1U_0603', 460, 1260, 90, '1uF', True, True, None),
        ('C278', 'C100N_0402', None, 540, 1260, 270, '100nF', True, True, None),
        ('C279', 'C1U_0603_TDK', 'C1U_0603', 620, 1260, 90, '1uF', True, True, None),

        # Box 3: VC Switch (U223) + P1-3 Level Shifter (U234/C290) + Buffer (U222.2) + OCXO (U218)
        ('U223', 'TS5A3159ADBVT', None, 2140, 1860, 0, 'TS5A3159ADBVT', True, True, None),
        ('U234', 'SN74AHCT1G125DBVR', None, 2170, 2040, 0, 'SN74AHCT1G125DBVR', True, True, None),
        ('C290', 'C100N_0402', None, 2260, 2040, 270, '100nF', True, True, None),
        ('R251', 'R100K_0402', None, 2260, 1915, 270, '100kΩ', True, True, None),
        ('C253', 'C100N_0402', None, 2230, 1735, 270, '100nF', True, True, None),
        ('U222', 'OPA2192IDR', None, 2400, 1860, 0, 'OPA2192IDR', True, True, 'OPA2192IDR.2'),
        ('R253', 'R10K_0402_V2', 'R10K_0402', 2540, 1780, 270, '10kΩ', True, True, None),
        ('R254', 'R10K_0402_V2', 'R10K_0402', 2540, 1650, 270, '10kΩ', True, True, None),
        ('C254', 'C10N_0402', None, 2610, 1650, 0, '10nF', True, True, None),
        ('R252', 'R100R_0402_V2', 'R100R_0402', 2690, 1860, 0, '100Ω', True, True, None),
        ('C252', 'C100N_0402', None, 2760, 1800, 270, '100nF', True, True, None),
        ('R238', 'POT_20K', 'POT_3296W_103', 2740, 1650, 0, '20kΩ', True, True, None),
        ('R239', 'R0R_0402', 'R0R_0603', 2820, 1710, 0, '0Ω(DNP)', False, True, None),
        ('U218', 'DOIFITQKY_100M', 'DOIFITQKY_100M_SYS', 2960, 1850, 0, 'DOIFITQKY-100M', True, True, None),
        ('L219', 'BLM18PG121SN1D', None, 3000, 1980, 0, 'BLM18PG121SN1D', True, True, None),
        ('C283', 'C47U_1206', None, 3140, 1940, 270, '47uF', True, True, None),
        ('C281', 'C1U_0603_TDK', 'C1U_0603', 3230, 1940, 90, '1uF', True, True, None),
        ('C282', 'C100N_0402', None, 3320, 1940, 270, '100nF', True, True, None),

        # Box 4 (Shifted LEDs dx=-1880)
        ('R263', 'R1K_0402', 'R1K_0603', 2170 + DX_LED, 755, 180, '1kΩ', True, True, None),
        ('LED_REF_LOCK', 'LED_G', None, 2270 + DX_LED, 755, 180, 'LED_GREEN', True, True, None),
        ('Q210', '2N7002', None, 2320 + DX_LED, 640, 0, '2N7002', True, True, None),
        ('R264', 'R1K_0402', 'R1K_0603', 2730 + DX_LED, 755, 180, '1kΩ', True, True, None),
        ('LED_REF_EXT', 'LED_Y', None, 2830 + DX_LED, 755, 180, 'LED_YELLOW', True, True, None),
        ('Q211', '2N7002', None, 2880 + DX_LED, 640, 0, '2N7002', True, True, None),
    ]

    # Filter already-placed when resuming
    to_place = []
    seen_u222 = existing_u222
    for row in specs:
        des = row[0]
        if des == 'U222':
            if seen_u222 >= 2:
                continue
            if seen_u222 == 1 and row[9] == 'OPA2192IDR.1':
                continue
            seen_u222 += 1
        elif des in existing_des:
            continue
        to_place.append(row)

    # Place remaining components in batches of 11
    for idx in range(0, len(to_place), 11):
        chunk = to_place[idx:idx + 11]
        payload = []
        for des, dk, fbk, x, y, rot, nm, bom, pcb, sub in chunk:
            d1 = DEVS[dk]
            d2 = DEVS[fbk] if fbk else d1
            payload.append({
                'des': des, 'lib1': d1[0], 'uuid1': d1[1], 'lib2': d2[0], 'uuid2': d2[1],
                'x': x, 'y': y, 'rot': rot, 'name': nm, 'bom': bom, 'pcb': pcb, 'sub': sub,
            })
        print(f"Placing REF_CLOCK batch {idx // 11 + 1}/{(len(specs) + 10) // 11} ({len(chunk)} comps)...")
        res = js(open_page(page_uuid, 350) + f"""
const items = {json.dumps(payload, ensure_ascii=False)};
const placed = [], failed = [];
for (const it of items) {{
  let c = null;
  try {{
    c = await eda.sch_PrimitiveComponent.create({{libraryUuid: it.lib1, uuid: it.uuid1}}, it.x, it.y, it.sub || undefined, it.rot, false, it.bom, it.pcb);
  }} catch(e) {{}}
  if (!c && (it.lib2 !== it.lib1 || it.uuid2 !== it.uuid1)) {{
    try {{
      c = await eda.sch_PrimitiveComponent.create({{libraryUuid: it.lib2, uuid: it.uuid2}}, it.x, it.y, it.sub || undefined, it.rot, false, it.bom, it.pcb);
    }} catch(e) {{}}
  }}
  if (!c) {{ failed.push(it.des); continue; }}
  const a = c.toAsync();
  a.setState_Designator(it.des);
  a.setState_Name(it.name);
  a.setState_AddIntoBom(it.bom);
  a.setState_AddIntoPcb(it.pcb);
  await a.done();
  placed.push(it.des);
}}
await new Promise(r => setTimeout(r, 150));
return {{placed, failed}};
""", timeout=180)
        if res['failed']:
            raise RuntimeError(f"REF_CLOCK placement failed: {res['failed']}")

    js(open_page(page_uuid, 300) + "await eda.sch_Document.save(); return 1;")

    # 3. Inspect live pins of all 65 instances to dynamically snap every wire endpoint!
    pg = dump_page(page_uuid)
    by_des = {}
    for c in pg['reals']:
        by_des.setdefault(c['des'], []).append(c)

    def get_c(des, unit=0):
        if des == 'U222':
            return next(c for c in by_des['U222'] if any(p[0] == ('1' if unit == 0 else '5') for p in c['pins']))
        return by_des[des][unit]

    def pxy(des, num=None, name=None, unit=0):
        for pn, pnm, px, py, _ in get_c(des, unit)['pins']:
            if num is not None and str(pn) == str(num):
                return round(px, 1), round(py, 1)
            if name is not None and str(pnm).upper() == name.upper():
                return round(px, 1), round(py, 1)
        raise KeyError((des, num, name, unit))

    def tb(des):
        p1, p2 = get_c(des)['pins'][0], get_c(des)['pins'][1]
        a, b = (round(p1[2], 1), round(p1[3], 1)), (round(p2[2], 1), round(p2[3], 1))
        return (a, b) if a[1] > b[1] else (b, a)

    def lr(des):
        p1, p2 = get_c(des)['pins'][0], get_c(des)['pins'][1]
        a, b = (round(p1[2], 1), round(p1[3], 1)), (round(p2[2], 1), round(p2[3], 1))
        return (a, b) if a[0] < b[0] else (b, a)

    # Inspect all placed components vs ref_clock_v2_pins.json & print U234/C290/R265/R266/diffs!
    base_v2 = r'C:\Users\Jo1yc\.gemini\antigravity\brain\b58dc453-92ee-41d6-996e-8b11784c80ff\scratch\ref_clock_v2_pins.json'
    rp_v2 = json.load(open(base_v2, encoding='utf-8'))['result']['pinDump']
    print("=== Pin comparison vs ref_clock_v2 ===")
    for c in pg['reals']:
        des = c['des']
        if des in ('U234', 'C290', 'R265', 'R266'):
            print(f"  NEW {des:6s} @{c['x']},{c['y']}: {[(p[0],p[1],round(p[2],1),round(p[3],1),p[4]) for p in c['pins']]}")
            continue
        # Map +200 back to v2 key (and undo DX_LED on LEDs)
        v2k = des
        if des == 'U222':
            v2k = 'U22.1' if any(p[0] == '1' for p in c['pins']) else 'U22.2'
        elif des[0] in ('R', 'C', 'U', 'D', 'L', 'Q') and des[1:].isdigit():
            v2k = des[0] + str(int(des[1:]) - 200)
        if v2k in rp_v2:
            v2c = rp_v2[v2k]
            v2_offs = sorted((str(p['num']), round(p['x'] - v2c['x'], 1), round(p['y'] - v2c['y'], 1)) for p in v2c['pins'])
            live_offs = sorted((str(p[0]), round(p[2] - c['x'], 1), round(p[3] - c['y'], 1)) for p in c['pins'])
            if v2_offs != live_offs:
                print(f"  DIFF {des:6s} ({v2k}): v2={v2_offs} vs live={live_offs}")

    if '--place-only' in sys.argv:
        json.dump({'page_uuid': page_uuid, 'reals': pg['reals']}, open(r'c:\Users\Jo1yc\Desktop\硕士课题\_agent_tmp\ref_clock_live_pins.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
        print("Saved ref_clock_live_pins.json cleanly.")
        return page_uuid

    # Helper to stitch 2-pin inline component into a golden horizontal/vertical endpoint nicely!
    flags = []   # ('Ground'/'Power', net, x, y, 0)
    ports = []   # ('IN'/'OUT', net, x, y, rot)
    wires = []   # ([x0,y0,...], net_or_None)

    # --- Flags from polish_ref_a / polish_ref_c (with P1-1 D201 moved to 620,2110 & LEDs shifted -1880 & no Box 4 LDO) ---
    flags.extend([
        # Box 1
        ('Ground', 'GND', 160, 2250, 0),
        ('Ground', 'GND', 210, 2155, 0),
        ('Ground', 'GND', 310, 2085, 0),
        ('Ground', 'GND', 390, 2115, 0),
        ('Ground', 'GND', 570, 2100, 0),
        ('Power', '3V3_REF', 620, 2110, 0),   # D201 cathode shifted slightly left for P1-1 R266
        ('Power', '3V3_REF', 655, 2295, 0),   # [P1-1] R265 top
        ('Ground', 'GND', 665, 2135, 0),      # [P1-1] R266 bot
        ('Power', '3V3_REF', 580, 2065, 0),
        ('Ground', 'GND', 580, 1910, 0),
        ('Ground', 'GND', 650, 1910, 0),
        ('Power', '3V3_REF', 625, 1960, 0),
        ('Power', '3V3_REF', 890, 1985, 0),
        ('Ground', 'GND', 890, 1915, 0),
        # ADF4002 & LF
        ('Ground', 'GND', 865, 2315, 0),
        ('Ground', 'GND', 970, 2360, 0),
        ('Power', '3V3_REF', 985, 2225, 0),
        ('Power', '5VA_REF', 1170, 2315, 0),
        ('Power', '3V3_REF', 1200, 2305, 0),
        ('Power', '3V3_REF', 1280, 2370, 0),
        ('Power', '3V3_REF', 1280, 2160, 0),
        ('Ground', 'GND', 1170, 2185, 0),
        ('Power', '3V3_REF', 980, 2005, 0),
        ('Ground', 'GND', 1125, 1895, 0),
        ('Power', '5VA_REF', 1320, 2005, 0),
        ('Ground', 'GND', 1385, 1895, 0),
        ('Ground', 'GND', 1680, 2140, 0),
        # Box 2: Vref Buffer (U222.1) + Calibration DAC (U221)
        ('Power', '5VA_REF', 420, 1630, 0),
        ('Ground', 'GND', 420, 1495, 0),
        ('Ground', 'GND', 580, 1460, 0),
        ('Power', '5VA_REF', 675, 1600, 0),
        ('Ground', 'GND', 865, 1620, 0),
        ('Power', '3V3_REF', 930, 1455, 0),
        ('Ground', 'GND', 1220, 1350, 0),
        ('Power', '5VA_REF', 320, 1315, 0),
        ('Ground', 'GND', 500, 1205, 0),
        # Box 3: U223 + U234 + U222.2 + OCXO
        ('Ground', 'GND', 2070, 1810, 0),
        ('Ground', 'GND', 2260, 1880, 0),
        ('Power', '5VA_REF', 2250, 1795, 0),
        ('Ground', 'GND', 2230, 1700, 0),
        ('Power', '5VA_REF', 2260, 2080, 0),   # [P1-3] U234/C290 5VA_REF
        ('Ground', 'GND', 2120, 2005, 0),      # [P1-3] U234 OE#/GND dedicated GND
        ('Ground', 'GND', 2260, 1995, 0),      # [P1-3] C290 GND
        ('Ground', 'GND', 2575, 1585, 0),
        ('Ground', 'GND', 2760, 1760, 0),
        ('Ground', 'GND', 2690, 1630, 0),
        ('Ground', 'GND', 2880, 1790, 0),
        ('Power', '5vosc', 2940, 2000, 0),
        ('Ground', 'GND', 3230, 1885, 0),
        # Box 4: Status LEDs (shifted dx=-1880)
        ('Power', '3V3_REF', 2120 + DX_LED, 780, 0),
        ('Ground', 'GND', 2330 + DX_LED, 590, 0),
        ('Power', '3V3_REF', 2680 + DX_LED, 780, 0),
        ('Ground', 'GND', 2890 + DX_LED, 590, 0),
    ])

    # Raw createNetPort orientation:
    # - Right side (wire enters from left): OUT/BI -> rot=0, IN -> rot=180
    # - Left side  (wire enters from right): OUT/BI -> rot=180, IN -> rot=0
    ports.extend([
        ('OUT', 'EXTREF_DET', 795, 1915, 0),
        ('IN', 'CLK_FB_N', 810, 2295, 0),
        ('IN', 'CLK_FB_P', 810, 2245, 0),
        ('OUT', 'REF_LOCK', 1350, 2415, 0),
        ('IN', 'ADF_LE', 1350, 2310, 180),
        ('IN', 'SPI_REF_MOSI', 1350, 2245, 180),
        ('IN', 'SPI_REF_SCK', 1350, 2205, 180),
        ('IN', 'ADF_CE', 1350, 2090, 180),
        ('IN', 'OCXO_VREF', 240, 1550, 0),
        ('IN', 'SPI_REF_MOSI', 950, 1580, 180),
        ('IN', 'SPI_REF_SCK', 950, 1540, 180),
        ('IN', 'DAC_SYNC_N', 950, 1495, 180),
        ('IN', 'REF_SEL', 2040, 2040, 0),   # [P1-3] straight horizontal into U234.A!
        ('OUT', 'VC_MON', 2690, 1720, 0),
        ('OUT', 'OCXO_VREF', 2970, 1650, 0),
        ('OUT', 'OCXO_RF', 3140, 1840, 0),
        ('IN', 'REF_LOCK', 2160 + DX_LED, 640, 0),
        ('IN', 'REF_SEL', 2720 + DX_LED, 640, 0),
    ])

    # --- Wires (strict single-label rule: IN ports/flags/vertical/short jumpers pass net=None!) ---
    c245_l, c245_r = lr('C245')
    c246_l, c246_r = lr('C246')
    c247_t, c247_b = tb('C247')
    r247_t, r247_b = tb('R247')
    c248_t, c248_b = tb('C248')
    r248_l, r248_r = lr('R248')
    c249_t, c249_b = tb('C249')
    c250_t, c250_b = tb('C250')
    c283_t, c283_b = tb('C283')
    c281_t, c281_b = tb('C281')
    c282_t, c282_b = tb('C282')
    r265_t, r265_b = tb('R265')
    r266_t, r266_b = tb('R266')

    # Box 1 + ADF4002 + LF
    wires.extend([
        ([200, 2245, 200, 2255, 220, 2255, 220, 2245], None),
        ([200, 2255, 160, 2255, 160, 2250], None),
        ([200, 2185, 200, 2175, 220, 2175, 220, 2185], None),
        ([210, 2175, 210, 2155], None),
        ([240, 2215, 295, 2215], 'EXTREF_IN'),
        ([295, 2215, 470, 2215], None),
        ([310, 2185, 310, 2215], None),
        ([310, 2105, 310, 2085], None),
        ([390, 2175, 390, 2215], None),
        ([390, 2135, 390, 2115], None),
        ([415, 2215, 415, 1990, 435, 1990], None),
        # EXTREF_AC (label on 75u segment away from R265/R266/D201)
        ([510, 2215, 585, 2215], 'EXTREF_AC'),
        ([585, 2215, 600, 2215, 655, 2215, 665, 2215, 700, 2215], None),
        ([600, 2175, 600, 2215], None),
        ([590, 2125, 570, 2125, 570, 2100], None),
        ([610, 2125, 610, 2095, 620, 2095, 620, 2110], None),
        # [P1-1] R265 & R266 bias
        ([r265_t[0], r265_t[1], 655, 2295], None),
        ([r265_b[0], r265_b[1], 655, 2215], None),
        ([r266_t[0], r266_t[1], 665, 2215], None),
        ([r266_b[0], r266_b[1], 665, 2135], None),
        # ADF_REFIN straight horizontal along y=2215 (C245/R245 safely above at y=2245..2295!)
        ([740, 2215, 980, 2215], 'ADF_REFIN'),
        ([980, 2215, 1025, 2215], None),
        # U224 Detect (single EXTREF_DET label on [665..795, 1915])
        ([475, 1990, 580, 1990], 'EXTREF_DET_AC'),
        ([580, 1990, 680, 1990], None),
        ([580, 2055, 580, 2065], None),
        ([580, 2015, 580, 1990], None),
        ([580, 1965, 580, 1990], None),
        ([580, 1925, 580, 1910], None),
        ([680, 1980, 650, 1980, 650, 1910], None),
        ([680, 1970, 665, 1970, 665, 1915], None),
        ([665, 1915, 795, 1915], 'EXTREF_DET'),
        ([680, 1960, 625, 1960], None),
        ([890, 1970, 890, 1985], None),
        ([890, 1930, 890, 1915], None),
        # ADF4002 RF_FB (IN ports carry built-in label -> wire net=None!)
        ([810, 2295, c246_l[0], 2295], None),
        ([875, 2290, 875, 2295], None),
        ([810, 2245, c245_l[0], 2245], None),
        ([875, 2250, 875, 2245], None),
        ([c246_r[0], 2295, 975, 2295, 975, 2245, 1025, 2245], None),
        ([c245_r[0], 2245, 955, 2245, 955, 2235, 1025, 2235], None),
        ([1025, 2225, 985, 2225], None),
        ([1025, 2255, 1005, 2255, 1005, 2370, 970, 2370, 970, 2360], None),
        ([1025, 2265, 1005, 2265], None),
        ([1025, 2285, 950, 2285, 950, 2335, 930, 2335], None),
        ([890, 2335, 865, 2335, 865, 2315], None),
        ([1025, 2275, 990, 2275, 990, 2460, 1020, 2460], None),
        ([1020, 2460, 1540, 2460], 'LF_CP'),
        ([1540, 2460, 1540, 2380, r248_l[0], 2380], None),
        ([1135, 2285, 1170, 2285, 1170, 2315], None),
        ([1135, 2275, 1200, 2275, 1200, 2305], None),
        # U220 right side fanned out to y = 2415 / 2310 / 2245 / 2205 / 2090!
        ([1135, 2265, 1195, 2265, 1195, 2415], None),
        ([1195, 2415, 1350, 2415], 'REF_LOCK'),
        ([1135, 2255, 1215, 2255, 1215, 2310, 1350, 2310], None),
        ([1280, 2315, 1280, 2310], None),
        ([1280, 2355, 1280, 2370], None),
        ([1135, 2245, 1350, 2245], None),
        ([1135, 2235, 1215, 2235, 1215, 2205, 1350, 2205], None),
        ([1135, 2225, 1200, 2225, 1200, 2090, 1350, 2090], None),
        ([1280, 2105, 1280, 2090], None),
        ([1280, 2145, 1280, 2160], None),
        ([1135, 2215, 1170, 2215, 1170, 2185], None),
        # ADF4002 decoupling caps C270..C275
        ([980, 2005, 980, 1990, 1230, 1990], None),
        ([1020, 1970, 1020, 1990], None),
        ([1090, 1970, 1090, 1990], None),
        ([1160, 1970, 1160, 1990], None),
        ([1230, 1970, 1230, 1990], None),
        ([1020, 1930, 1020, 1910, 1230, 1910, 1230, 1930], None),
        ([1090, 1930, 1090, 1910], None),
        ([1160, 1930, 1160, 1910], None),
        ([1125, 1910, 1125, 1895], None),
        ([1320, 2005, 1320, 1990, 1420, 1990], None),
        ([1350, 1970, 1350, 1990], None),
        ([1420, 1970, 1420, 1990], None),
        ([1350, 1930, 1350, 1910, 1420, 1910, 1420, 1930], None),
        ([1385, 1910, 1385, 1895], None),
        # Loop filter (snapped to live c247/r247/c248/r248/c249; LF_OUT label ONLY on top horizontal segment!)
        ([c247_t[0], c247_t[1], 1540, 2380], None),
        ([r247_t[0], r247_t[1], 1640, 2380], None),
        ([r247_b[0], r247_b[1], c248_t[0], c248_t[1]], None),
        ([c249_t[0], c249_t[1], 1820, 2380], None),
        ([c247_b[0], c247_b[1], 1540, 2160, 1820, 2160, c249_b[0], c249_b[1]], None),
        ([c248_b[0], c248_b[1], 1640, 2160], None),
        ([1680, 2160, 1680, 2140], None),
        ([r248_r[0], 2380, 2030, 2380], 'LF_OUT'),
        ([2030, 2380, 2030, 1870, 2105, 1870], None),
    ])

    # Box 2: U222.1 + U221 DAC8551 + Decaps C276..C279 (clean horizontal labels only, IN wires net=None)
    wires.extend([
        ([240, 1550, 380, 1550], None),
        ([420, 1600, 420, 1630], None),
        ([420, 1520, 420, 1495], None),
        ([380, 1570, 350, 1570, 350, 1660, 490, 1660, 490, 1560], None),
        ([460, 1560, 580, 1560], None),
        ([580, 1560, 715, 1560], 'DAC_VREF'),
        ([580, 1520, 580, 1560], None),
        ([580, 1480, 580, 1460], None),
        ([715, 1570, 675, 1570, 675, 1600], None),
        ([715, 1550, 685, 1550, 685, 1540], None),
        ([715, 1540, 685, 1540, 685, 1440, 740, 1440], None),
        ([740, 1440, 1100, 1440], 'DAC_VOUT'),
        # U221 GND up clear at y=1625 & 3 IN ports fanned to y=1580 / 1540 / 1495 (net=None!)
        ([805, 1570, 825, 1570, 825, 1625, 865, 1625, 865, 1620], None),
        ([805, 1560, 845, 1560, 845, 1580, 950, 1580], None),
        ([805, 1550, 860, 1550, 860, 1540, 950, 1540], None),
        ([805, 1540, 845, 1540, 845, 1495, 950, 1495], None),
        ([860, 1460, 860, 1495], None),
        ([900, 1460, 930, 1460, 930, 1455], None),
        ([1140, 1440, 2010, 1440], 'DAC_VC'),
        ([2010, 1440, 2010, 1850, 2105, 1850], None),
        ([c250_t[0], c250_t[1], 1220, 1440], None),
        ([c250_b[0], c250_b[1], 1220, 1350], None),
        ([320, 1315, 320, 1300, 620, 1300], None),
        ([380, 1280, 380, 1300], None),
        ([460, 1280, 460, 1300], None),
        ([540, 1280, 540, 1300], None),
        ([620, 1280, 620, 1300], None),
        ([380, 1240, 380, 1220, 620, 1220, 620, 1240], None),
        ([460, 1240, 460, 1220], None),
        ([540, 1240, 540, 1220], None),
        ([500, 1220, 500, 1205], None),
    ])

    # Box 3: [P1-3] U234/C290 -> U223 -> U222.2 -> OCXO
    u234_oe = pxy('U234', name='OE#') if any('OE' in str(p[1]).upper() for p in get_c('U234')['pins']) else pxy('U234', num='1')
    u234_a = pxy('U234', name='A')
    u234_gnd = pxy('U234', name='GND')
    u234_y = pxy('U234', name='Y')
    u234_vcc = pxy('U234', name='VCC')
    c290_t, c290_b = tb('C290')

    wires.extend([
        # REF_SEL NetPort(2040, 2040, rot=0) -> R251 & straight into U234.A (zero near-miss on y=2030!)
        ([2040, 2040, 2070, 2040, u234_a[0], u234_a[1]], None),
        ([2070, 2040, 2070, 1960, 2260, 1960, 2260, 1935], None),
        ([2260, 1895, 2260, 1880], None),
        ([u234_oe[0], u234_oe[1], u234_oe[0] - 15, u234_oe[1], u234_oe[0] - 15, u234_gnd[1], u234_gnd[0], u234_gnd[1]], None),
        ([u234_gnd[0] - 15, u234_gnd[1], 2120, 2005], None),
        ([u234_vcc[0], u234_vcc[1], 2225, u234_vcc[1], 2225, 2070, c290_t[0], 2070], None),
        ([c290_t[0], c290_t[1], c290_t[0], 2080], None),
        ([c290_b[0], c290_b[1], c290_b[0], 1995], None),
        # U234.Y -> REF_SEL_5V at x=2195 (40u clear of U223 V+ at x=2235!)
        ([u234_y[0], u234_y[1], 2215, u234_y[1], 2215, 1980, 2195, 1980, 2195, 1870, 2175, 1870], None),
        # U223 & U222.2 & R252..R239 & U218 (VC_SW routed along y=1830, 30u below U223.V+!)
        ([2105, 1860, 2070, 1860, 2070, 1810], None),
        ([2175, 1860, 2230, 1860, 2230, 1780, 2250, 1780, 2250, 1795], None),
        ([2230, 1755, 2230, 1780], None),
        ([2230, 1715, 2230, 1700], None),
        ([2175, 1850, 2205, 1850, 2205, 1830], None),
        ([2205, 1830, 2340, 1830], 'VC_SW'),
        ([2340, 1830, 2340, 1850, 2360, 1850], None),
        ([2360, 1870, 2330, 1870, 2330, 1930, 2480, 1930, 2480, 1860], None),
        ([2440, 1860, 2480, 1860], None),
        ([2480, 1860, 2670, 1860], 'VC_BUF'),
        ([2540, 1800, 2540, 1860], None),
        ([2540, 1760, 2540, 1670], None),
        ([2540, 1720, 2610, 1720], None),
        ([2610, 1720, 2690, 1720], 'VC_MON'),
        ([2610, 1670, 2610, 1720], None),
        ([2540, 1630, 2540, 1600, 2610, 1600, 2610, 1630], None),
        ([2575, 1600, 2575, 1585], None),
        ([2710, 1860, 2760, 1860], None),
        ([2760, 1860, 2910, 1860], 'OCXO_VC'),
        ([2760, 1820, 2760, 1860], None),
        ([2760, 1780, 2760, 1760], None),
        ([2720, 1650, 2690, 1650, 2690, 1630], None),
        ([2740, 1670, 2740, 1710, 2800, 1710], None),
        ([2840, 1710, 2840, 1860], None),
        ([2910, 1850, 2870, 1850, 2870, 1650, 2760, 1650], None),
        ([2870, 1650, 2970, 1650], 'OCXO_VREF'),
        ([2910, 1840, 2880, 1840, 2880, 1790], None),
        ([3000, 1840, 3140, 1840], 'OCXO_RF'),
        ([2940, 2000, 2940, 1980, 2980, 1980], None),
        ([3000, 1860, 3040, 1860, 3040, 1980, 3020, 1980], None),
        ([3040, 1980, 3140, 1980], 'OCXO_5V_FILT'),
        ([3140, 1980, 3320, 1980], None),
        ([c283_t[0], c283_t[1], 3140, 1980], None),
        ([c281_t[0], c281_t[1], 3230, 1980], None),
        ([c282_t[0], c282_t[1], 3320, 1980], None),
        ([c283_b[0], c283_b[1], 3140, 1900, 3320, 1900, c282_b[0], c282_b[1]], None),
        ([c281_b[0], c281_b[1], 3230, 1900], None),
        ([3230, 1900, 3230, 1885], None),
    ])

    # Box 4: Status LEDs shifted DX_LED=-1880 (IN ports net=None, clean horizontal stubs)
    wires.extend([
        ([2150 + DX_LED, 755, 2120 + DX_LED, 755, 2120 + DX_LED, 780], None),
        ([2190 + DX_LED, 755, 2250 + DX_LED, 755], 'LED_LOCK_A'),
        ([2290 + DX_LED, 755, 2330 + DX_LED, 755, 2330 + DX_LED, 660], None),
        ([2160 + DX_LED, 640, 2300 + DX_LED, 640], None),
        ([2330 + DX_LED, 620, 2330 + DX_LED, 590], None),
        ([2710 + DX_LED, 755, 2680 + DX_LED, 755, 2680 + DX_LED, 780], None),
        ([2750 + DX_LED, 755, 2810 + DX_LED, 755], 'LED_EXT_A'),
        ([2850 + DX_LED, 755, 2890 + DX_LED, 755, 2890 + DX_LED, 660], None),
        ([2720 + DX_LED, 640, 2860 + DX_LED, 640], None),
        ([2890 + DX_LED, 620, 2890 + DX_LED, 590], None),
    ])

    # --- Preflight Graph Verification BEFORE writing to EasyEDA ---
    bad_rots = [fl for fl in flags if fl[4] != 0]
    if bad_rots:
        raise RuntimeError(f"Non-zero rot flags found: {bad_rots}")
    f_v, rn_v = verify_graph(pg['reals'], flags, ports, wires)
    shorts = []
    for c in pg['reals']:
        for pn, pnm, px, py, _ in c['pins']:
            ns = rn_v.get(f_v((round(px, 1), round(py, 1))), set())
            if len(ns) > 1:
                shorts.append((c['des'], pn, pnm, sorted(ns)))
    if shorts:
        raise RuntimeError(f"REF_CLOCK PREFLIGHT SHORTS: {shorts}")
    root_pin_cnt = {}
    for c in pg['reals']:
        for _, _, px, py, _ in c['pins']:
            r = f_v((round(px, 1), round(py, 1)))
            root_pin_cnt[r] = root_pin_cnt.get(r, 0) + 1
    floating = []
    for c in pg['reals']:
        for pn, pnm, px, py, _ in c['pins']:
            if c['des'] == 'U224' and str(pn) == '1':
                continue
            r = f_v((round(px, 1), round(py, 1)))
            ns = rn_v.get(r, set())
            if len(ns) == 0 and root_pin_cnt.get(r, 0) < 2:
                floating.append((c['des'], pn, pnm, sorted(ns)))
    if floating:
        raise RuntimeError(f"REF_CLOCK PREFLIGHT FLOATING PINS: {floating}")
    # Also verify exact point-to-point pairs for unnamed internal links
    for a_xy, b_xy, lbl in [
        (pxy('C246', '2'), pxy('U220', name='RFINB'), 'ADF_RFINB'),
        (pxy('C245', '2'), pxy('U220', name='RFINA'), 'ADF_RFINA'),
        (pxy('R246', '1'), pxy('U220', name='RSET'), 'ADF_RSET'),
        (r247_b, c248_t, 'LF_Z'),
        (pxy('R238', '2'), pxy('R239', '1'), 'R238_WIPER'),
        (pxy('LED_REF_LOCK', '1'), pxy('Q210', name='D'), 'LED_LOCK_K'),
        (pxy('LED_REF_EXT', '1'), pxy('Q211', name='D'), 'LED_EXT_K'),
    ]:
        if f_v(a_xy) != f_v(b_xy):
            raise RuntimeError(f"REF_CLOCK unnamed link broken: {lbl}")
    unconn_fp = []
    for fl in flags:
        if fl[1] not in rn_v.get(f_v((round(fl[2], 1), round(fl[3], 1))), set()):
            unconn_fp.append(('flag', fl))
    for np in ports:
        if np[1] not in rn_v.get(f_v((round(np[2], 1), round(np[3], 1))), set()):
            unconn_fp.append(('port', np))
    if unconn_fp:
        raise RuntimeError(f"REF_CLOCK UNCONNECTED FLAGS/PORTS: {unconn_fp}")
    # Check P1-1 & P1-3 & key nets!
    if f_v(r265_b) != f_v((600, 2215)) or f_v(r266_t) != f_v((600, 2215)):
        raise RuntimeError("P1-1 R265/R266 not joined to EXTREF_AC!")
    if '3V3_REF' not in rn_v.get(f_v(r265_t), set()) or 'GND' not in rn_v.get(f_v(r266_b), set()):
        raise RuntimeError("P1-1 R265/R266 bias rails missing!")
    u234_y_ns = rn_v.get(f_v(u234_y), set())
    if f_v(u234_y) != f_v(pxy('U223', name='IN')):
        raise RuntimeError(f"P1-3 U234.Y {u234_y_ns} not joined to U223.IN!")
    if f_v(u234_a) != f_v((2040, 2040)):
        raise RuntimeError("P1-3 U234.A not connected to REF_SEL!")
    print(f"REF_CLOCK PREFLIGHT PASSED 100%! wires={len(wires)}, flags={len(flags)}, ports={len(ports)}, shorts=0, P1-1=OK, P1-3=OK")

    # 4. Clear any partial flags/ports/wires on resume, open page once, and write in batches <= 35
    if pg['flags'] or pg['wires']:
        old_fids = [f['pid'] for f in pg['flags']]
        old_wids = [w['pid'] for w in pg['wires']]
        print(f"Clearing partial flags/ports ({len(old_fids)}) & wires ({len(old_wids)}) in batches of 30...")
        js(open_page(page_uuid, 600) + "return 1;")
        for i in range(0, len(old_fids), 30):
            js(f"for (const id of {json.dumps(old_fids[i:i+30])}) await eda.sch_PrimitiveComponent.delete(id); return 1;")
        for i in range(0, len(old_wids), 30):
            js(f"for (const id of {json.dumps(old_wids[i:i+30])}) await eda.sch_PrimitiveWire.delete(id); return 1;")
        js("await new Promise(r => setTimeout(r, 200)); return 1;")
    else:
        js(open_page(page_uuid, 600) + "return 1;")

    ops = [('flag', x) for x in flags] + [('port', x) for x in ports] + [('wire', x) for x in wires]
    for idx in range(0, len(ops), 20):
        chunk = ops[idx:idx + 20]
        cf = [x for t, x in chunk if t == 'flag']
        cp = [x for t, x in chunk if t == 'port']
        cw = [x for t, x in chunk if t == 'wire']
        print(f"  REF_CLOCK batch {idx // 20 + 1}/{(len(ops) + 19) // 20} ({len(chunk)} items)...")
        bres = js(f"""
const errs = [];
for (const [kind, net, x, y, rot] of {json.dumps(cf)}) {{
  try {{ await eda.sch_PrimitiveComponent.createNetFlag(kind, net, x, y, rot, false); }}
  catch (e) {{ errs.push(['flag', kind, net, x, y, String(e)]); }}
}}
for (const [dir, net, x, y, rot] of {json.dumps(cp)}) {{
  try {{ await eda.sch_PrimitiveComponent.createNetPort(dir, net, x, y, rot, false); }}
  catch (e) {{ errs.push(['port', dir, net, x, y, String(e)]); }}
}}
for (const [line, net] of {json.dumps(cw)}) {{
  try {{
    const w = await (net ? eda.sch_PrimitiveWire.create(line, net) : eda.sch_PrimitiveWire.create(line));
    if (!w) errs.push(['wire_null', line, net]);
  }} catch (e) {{ errs.push(['wire_err', line, net, String(e)]); }}
}}
await new Promise(r => setTimeout(r, 120));
return errs;
""", timeout=180)
        if bres:
            raise RuntimeError(f"REF_CLOCK batch error: {bres}")

    # 5. Boxes & Titles + Save
    boxes = [
        [100, 2560, 1840, 720, '1. 外部10MHz参考输入、偏置整形与ADF4002锁相环 (J_REFIN → U220 → 环路滤波)', '已合入 [P1-1] R265/R266 10kΩ 对 3V3_REF/GND 1.65V 偏置; C247/C248/C249 为实装薄膜/C0G'],
        [100, 1800, 1840, 660, '2. 内部参考Vref缓冲 (U222A) 与16-bit校准DAC (U221 DAC8551 → 1.6Hz低通)', 'VFB已接VOUT; 3V3_REF 与 5VA_REF 由电源页 LDO 统一提供'],
        [1980, 2560, 1480, 1420, '3. REF_SEL电平缓冲 (U234 [P1-3]) → VC模式切换 (U223) → 隔离缓冲 (U222B) → 100MHz OCXO (U218)', '已合入 [P1-3] U234 SN74AHCT1G125DBVR (3.3V→5V TTL驱动 U223); R239=0Ω(DNP)'],
        [100, 1080, 1480, 640, '4. 状态指示LED驱动 (Q210/LED_REF_LOCK绿灯 & Q211/LED_REF_EXT黄灯)', '已去除重复LDO与J_H1(全信号由sign页H1统一扇出); REF_LOCK=1亮绿灯; REF_SEL=1亮黄灯'],
    ]
    js(f"""
for (const [x, topY, w, h, title, note] of {json.dumps(boxes, ensure_ascii=False)}) {{
  await eda.sch_PrimitiveRectangle.create(x, topY, w, h, 0, 0, '#000000', 'none', 1, null, null);
  await eda.sch_PrimitiveText.create(x + 25, topY - 25, title, 0, '#000000', null, 18, true, false, false, 1);
  await eda.sch_PrimitiveText.create(x + 25, topY - h + 30, note, 0, '#555555', null, 10, false, false, false, 1);
}}
await eda.dmt_Schematic.modifySchematicPageName({json.dumps(page_uuid)}, {json.dumps(PAGE_NAME)});
await new Promise(r => setTimeout(r, 250));
await eda.sch_Document.save();
return 1;
""")

    # Read-back verification
    pg_fin = dump_page(page_uuid)
    offgrid = []
    for c in pg_fin['reals']:
        for pn, _, px, py, _ in c['pins']:
            best = 999.0
            for w in pg_fin['wires']:
                ln = w['line']
                for i in range(0, len(ln), 2):
                    d = math.hypot(px - ln[i], py - ln[i + 1])
                    if d < best:
                        best = d
            if 0.02 < best < 5.0:
                offgrid.append((c['des'], pn, round(best, 3)))
    print(f"REF_CLOCK LIVE VERIFY: uuid={page_uuid}, reals={len(pg_fin['reals'])}, flags={len(pg_fin['flags'])}, wires={len(pg_fin['wires'])}, offgrid={offgrid}")
    return page_uuid


if __name__ == '__main__':
    run()
