# -*- coding: utf-8 -*-
"""Step D2: Create & populate 'CLK_DIST' page in NVmw (+200 offset, P0-1, P0-2, P1-2, P2-1 fixes)."""
import json
import math
import sys

sys.path.insert(0, r'c:\Users\Jo1yc\Desktop\硕士课题\_agent_tmp')
from nvmw_lib import DEVS, SCHEMATIC_UUID, dump_page, get_pages, js, open_page

PAGE_NAME = 'CLOCK_DIST'


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
    # 1. Create clean CLK_DIST page (or reuse if --wire-only passed)
    page_uuid = None
    for p in get_pages():
        if '--wire-only' in sys.argv and p['name'] in ('CLKDIST', 'P1'):
            pg_chk = dump_page(p['uuid'])
            if any(c['des'] == 'U225' for c in pg_chk['reals']):
                page_uuid = p['uuid']
                js(f"await eda.dmt_Schematic.modifySchematicPageName({json.dumps(page_uuid)}, {json.dumps(PAGE_NAME)}); return 1;")
                break
        elif p['name'] == PAGE_NAME:
            js(f"await eda.dmt_Schematic.deleteSchematicPage({json.dumps(p['uuid'])}); await new Promise(r=>setTimeout(r,1000)); return 1;")

    if not page_uuid:
        page_uuid = js(f"return await eda.dmt_Schematic.createSchematicPage({json.dumps(SCHEMATIC_UUID)});")
        if not page_uuid:
            raise RuntimeError("createSchematicPage failed for CLK_DIST")
        js(open_page(page_uuid, 900) + f"await eda.dmt_Schematic.modifySchematicPageName({json.dumps(page_uuid)}, {json.dumps(PAGE_NAME)}); await new Promise(r=>setTimeout(r,300)); return 1;")
        print(f"Created & opened '{PAGE_NAME}' page: {page_uuid}")

        # 30 components matching stage2a_clk_v2.js layout with +200 designators
        specs = [
            ('R255', 'R49R9_0402', None, 290, 1345, 270, '49.9Ω', True, True),
            ('C255', 'C100N_0402', None, 370, 1405, 0, '100nF', True, True),
            ('C256', 'C100N_0402', None, 380, 1320, 270, '100nF', True, True),
            ('U225', 'LTC6957HMS_2', None, 560, 1400, 0, 'LTC6957HMS-2', True, True),
            ('FB201', 'BLM18PG121SN1D', None, 280, 1140, 0, 'BLM18PG121SN1D', True, True),
            ('C293', 'C100N_0402', None, 370, 1100, 270, '100nF', True, True),
            ('C294', 'C1U_0402', 'C1U_0603', 450, 1100, 90, '1uF', True, True),

            ('R257', 'R100R_0402_V2', 'R100R_0402', 760, 1500, 270, '100Ω', True, True),
            ('U226', 'LMK1D1208RHDT', None, 1080, 1435, 0, 'LMK1D1208RHDT', True, True),
            ('FB202', 'BLM18PG121SN1D', None, 940, 1140, 0, 'BLM18PG121SN1D', True, True),
            ('C295', 'C100N_0402', None, 1030, 1100, 270, '100nF', True, True),
            ('C296', 'C100N_0402', None, 1110, 1100, 270, '100nF', True, True),
            ('C297', 'C100N_0402', None, 1190, 1100, 270, '100nF', True, True),
            ('C298', 'C1U_0402', 'C1U_0603', 1270, 1100, 90, '1uF', True, True),

            ('R258', 'R100R_0402_V2', 'R100R_0402', 1630, 1505, 270, '100Ω', True, True),
            ('U227', 'SN65LVDS2DBVT', None, 1720, 1465, 0, 'SN65LVDS2DBVT', True, True),
            ('U228', '74LVC163PW', None, 1960, 1450, 0, '74LVC163PW', True, True),
            ('U233', 'SN74LVC1G04', '74LVC1G04GW', 2110, 1310, 0, 'SN74LVC1G04', True, True),
            ('U229', '74LVC1G74DC', None, 2240, 1430, 0, '74LVC1G74DC', True, True),
            ('U230', '74LVC2G34GW', None, 2480, 1405, 0, '74LVC2G34GW', True, True),
            ('R260', 'R33R_0402', None, 2630, 1415, 0, '33Ω', True, True),
            ('C260', 'C100P_0402', None, 2720, 1355, 270, '100pF(DNP)', False, True),
            ('J_REFOUT', 'HL2_BNC_50KE', None, 2840, 1415, 180, 'HL2-BNC-50KE', True, True),
            ('FB203', 'BLM18PG121SN1D', None, 1680, 1140, 0, 'BLM18PG121SN1D', True, True),
            ('C299', 'C1U_0402', 'C1U_0603', 1780, 1100, 270, '1uF', True, True),
            ('C300', 'C100N_0402', None, 1860, 1100, 270, '100nF', True, True),
            ('C301', 'C100N_0402', None, 1940, 1100, 270, '100nF', True, True),
            ('C302', 'C100N_0402', None, 2020, 1100, 270, '100nF', True, True),
            ('C303', 'C100N_0402', None, 2100, 1100, 270, '100nF', True, True),
            ('C304', 'C100N_0402', None, 2180, 1100, 270, '100nF', True, True),
        ]
        for idx in range(0, len(specs), 10):
            chunk = specs[idx:idx + 10]
            payload = []
            for des, dk, fbk, x, y, rot, nm, bom, pcb in chunk:
                d1 = DEVS[dk]
                d2 = DEVS[fbk] if fbk else d1
                payload.append({
                    'des': des, 'lib1': d1[0], 'uuid1': d1[1], 'lib2': d2[0], 'uuid2': d2[1],
                    'x': x, 'y': y, 'rot': rot, 'name': nm, 'bom': bom, 'pcb': pcb,
                })
            print(f"Placing CLK_DIST batch {idx // 10 + 1}/{(len(specs) + 9) // 10} ({len(chunk)} comps)...")
            res = js(f"""
const items = {json.dumps(payload, ensure_ascii=False)};
const placed = [], failed = [];
for (const it of items) {{
  let c = null;
  try {{ c = await eda.sch_PrimitiveComponent.create({{libraryUuid: it.lib1, uuid: it.uuid1}}, it.x, it.y, undefined, it.rot, false, it.bom, it.pcb); }} catch(e) {{}}
  if (!c && (it.lib2 !== it.lib1 || it.uuid2 !== it.uuid1)) {{
    try {{ c = await eda.sch_PrimitiveComponent.create({{libraryUuid: it.lib2, uuid: it.uuid2}}, it.x, it.y, undefined, it.rot, false, it.bom, it.pcb); }} catch(e) {{}}
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
                raise RuntimeError(f"CLK_DIST placement failed: {res['failed']}")
        js("await eda.sch_Document.save(); return 1;")

    pg = dump_page(page_uuid)
    by_des = {c['des']: c for c in pg['reals']}

    def pxy(des, num=None, name=None):
        for pn, pnm, px, py, _ in by_des[des]['pins']:
            if num is not None and str(pn) == str(num):
                return round(px, 1), round(py, 1)
            if name is not None and str(pnm).upper() == name.upper():
                return round(px, 1), round(py, 1)
        raise KeyError((des, num, name))

    def tb(des):
        p1, p2 = by_des[des]['pins'][0], by_des[des]['pins'][1]
        a, b = (round(p1[2], 1), round(p1[3], 1)), (round(p2[2], 1), round(p2[3], 1))
        return (a, b) if a[1] > b[1] else (b, a)

    # Compare vs clk_dist_v2_pins
    base_v2 = r'C:\Users\Jo1yc\.gemini\antigravity\brain\b58dc453-92ee-41d6-996e-8b11784c80ff\scratch\clk_dist_v2_pins.json'
    cp_v2 = json.load(open(base_v2, encoding='utf-8'))['result']['pinDump']
    print("=== CLK_DIST live pin check vs v2 ===")
    for c in pg['reals']:
        des = c['des']
        v2k = des if des in cp_v2 else ('FB' + str(int(des[2:]) - 200) if des.startswith('FB') else (des[0] + str(int(des[1:]) - 200)))
        if v2k in cp_v2:
            v2c = cp_v2[v2k]
            v2_offs = sorted((str(p['num']), round(p['x'] - v2c['x'], 1), round(p['y'] - v2c['y'], 1)) for p in v2c['pins'])
            live_offs = sorted((str(p[0]), round(p[2] - c['x'], 1), round(p[3] - c['y'], 1)) for p in c['pins'])
            if v2_offs != live_offs:
                print(f"  DIFF {des:8s} ({v2k}): v2={v2_offs} vs live={live_offs}")

    if '--place-only' in sys.argv:
        return page_uuid

    # Build flags, staggered ports, and direct orthogonal wires (snapping C260 / R255.. / U233 live pins)
    flags = [
        # U25 LTC6957 block
        ('Ground', 'GND', 290, 1305, 0),
        ('Ground', 'GND', 380, 1275, 0),
        ('Ground', 'GND', 485, 1450, 0),
        ('Power', '3V3_U225', 460, 1450, 0),
        ('Ground', 'GND', 480, 1345, 0),
        ('Ground', 'GND', 635, 1450, 0),
        ('Power', '3V3_U225', 645, 1375, 0),
        ('Power', '3V3_REF', 230, 1155, 0),
        ('Power', '3V3_U225', 480, 1155, 0),
        ('Ground', 'GND', 410, 1045, 0),
        # U26 LMK1D1208 block
        ('Ground', 'GND', 960, 1510, 0),
        ('Power', '3V3_U226', 980, 1445, 0),
        ('Ground', 'GND', 1005, 1295, 0),
        ('Ground', 'GND', 1200, 1540, 0),
        ('Power', '3V3_U226', 1170, 1550, 0),
        ('Power', '3V3_U226', 1175, 1245, 0),
        ('Power', '3V3_REF', 890, 1155, 0),
        ('Power', '3V3_U226', 1310, 1155, 0),
        ('Ground', 'GND', 1150, 1045, 0),
        # Divider + 10MHz REFOUT block (with P1-2: D3,D1,D0 = 1 -> 3V3_DIV, D2 = 0 -> GND!)
        ('Power', '3V3_DIV', 1715, 1515, 0),
        ('Ground', 'GND', 1645, 1405, 0),
        ('Power', '3V3_DIV', 1895, 1525, 0),
        ('Ground', 'GND', 1810, 1410, 0),
        ('Ground', 'GND', 1900, 1395, 0),
        ('Power', '3V3_DIV', 2025, 1505, 0),
        ('Power', '3V3_DIV', 2025, 1370, 0),   # entered cleanly from below (y=1360)
        ('Ground', 'GND', 2040, 1265, 0),
        ('Power', '3V3_DIV', 1985, 1290, 0),
        ('Ground', 'GND', 2185, 1395, 0),
        ('Power', '3V3_DIV', 2305, 1465, 0),
        ('Power', '3V3_DIV', 2375, 1395, 0),
        ('Ground', 'GND', 2540, 1375, 0),
        ('Ground', 'GND', 2720, 1315, 0),
        ('Ground', 'GND', 2780, 1450, 0),
        ('Ground', 'GND', 2830, 1355, 0),
        ('Power', '3V3_REF', 1630, 1155, 0),
        ('Power', '3V3_DIV', 2220, 1155, 0),
        ('Ground', 'GND', 1980, 1045, 0),
    ]

    # OCXO_RF is left-side IN -> rot=0, wire net=None!
    # U226 OUT ports fanned out to 25-unit vertical spacing (y=1270..1445) -> zero overlap!
    ports = [
        ('IN', 'OCXO_RF', 190, 1405, 0),
        ('OUT', 'CLK100_DDSA_P', 850, 1365, 180),
        ('OUT', 'CLK100_DDSA_N', 850, 1325, 180),
        ('OUT', 'CLK100_DDSB_P', 1455, 1270, 0),
        ('OUT', 'CLK100_DDSB_N', 1455, 1295, 0),
        ('OUT', 'CLK100_LMXA_P', 1455, 1320, 0),
        ('OUT', 'CLK100_LMXA_N', 1455, 1345, 0),
        ('OUT', 'CLK100_LMXB_P', 1455, 1370, 0),
        ('OUT', 'CLK100_LMXB_N', 1455, 1395, 0),
        ('OUT', 'CLK_FB_P', 1455, 1420, 0),
        ('OUT', 'CLK_FB_N', 1455, 1445, 0),
    ]

    u233_a = pxy('U233', name='A')
    u233_g = pxy('U233', name='GND')
    u233_y = pxy('U233', name='Y')
    u233_v = pxy('U233', name='VCC')
    c260_t, c260_b = tb('C260')
    r260_1, r260_2 = by_des['R260']['pins'][0], by_des['R260']['pins'][1]
    r260_l = (round(r260_1[2], 1), round(r260_1[3], 1)) if r260_1[2] < r260_2[2] else (round(r260_2[2], 1), round(r260_2[3], 1))
    r260_r = (round(r260_2[2], 1), round(r260_2[3], 1)) if r260_1[2] < r260_2[2] else (round(r260_1[2], 1), round(r260_1[3], 1))

    wires = [
        # U25 LTC6957-2 (OCXO_RF IN port -> wire net=None; C255/C256 direct 2-pin local coupling -> net=None)
        ([190, 1405, 350, 1405], None),
        ([290, 1365, 290, 1405], None),
        ([290, 1325, 290, 1305], None),
        ([390, 1405, 510, 1405], None),
        ([380, 1340, 380, 1375, 460, 1375, 460, 1395, 510, 1395], None),
        ([380, 1300, 380, 1275], None),
        ([510, 1425, 495, 1425, 495, 1455, 485, 1455, 485, 1450], None),
        ([510, 1415, 460, 1415, 460, 1450], None),
        ([510, 1385, 480, 1385, 480, 1345], None),
        ([510, 1375, 480, 1375], None),
        ([610, 1425, 625, 1425, 625, 1455, 635, 1455, 635, 1450], None),
        ([610, 1375, 645, 1375], None),
        # U25 Decoupling bus
        ([230, 1155, 230, 1140, 260, 1140], None),
        ([300, 1140, 480, 1140, 480, 1155], None),
        ([370, 1120, 370, 1140], None),
        ([450, 1120, 450, 1140], None),
        ([370, 1080, 370, 1060, 450, 1060, 450, 1080], None),
        ([410, 1060, 410, 1045], None),
        # U25 -> U226 LVDS separated by 30u (y=1435 & y=1405), R257 taps at (785,1435) & (760,1405)
        ([610, 1415, 645, 1415, 645, 1435], None),
        ([645, 1435, 785, 1435], 'CLK_LVDS_P'),
        ([785, 1435, 975, 1435, 975, 1415, 1015, 1415], None),
        ([760, 1520, 785, 1520, 785, 1435], None),
        ([610, 1405, 645, 1405], None),
        ([645, 1405, 760, 1405], 'CLK_LVDS_N'),
        ([760, 1405, 1015, 1405], None),
        ([760, 1480, 760, 1405], None),
        # U226 LMK1D1208
        ([1015, 1495, 985, 1495, 985, 1515, 960, 1515, 960, 1510], None),
        ([1015, 1465, 985, 1465, 985, 1495], None),
        ([1015, 1425, 980, 1425, 980, 1445], None),
        ([1015, 1385, 985, 1385, 985, 1365], None),
        ([985, 1365, 850, 1365], 'CLK100_DDSA_P'),
        ([1015, 1375, 970, 1375, 970, 1325], None),
        ([970, 1325, 850, 1325], 'CLK100_DDSA_N'),
        ([1015, 1365, 1005, 1365, 1005, 1295], None),
        ([1145, 1505, 1185, 1505, 1185, 1545, 1200, 1545, 1200, 1540], None),
        ([1145, 1495, 1170, 1495, 1170, 1550], None),
        ([1145, 1365, 1160, 1365, 1160, 1235, 1175, 1235, 1175, 1245], None),
        # U226 OUT1..OUT4 clean 25u vertical fanout (1270..1445), horizontal label stubs out to x=1455!
        ([1145, 1375, 1175, 1375, 1175, 1270], None),
        ([1175, 1270, 1455, 1270], 'CLK100_DDSB_P'),
        ([1145, 1385, 1190, 1385, 1190, 1295], None),
        ([1190, 1295, 1455, 1295], 'CLK100_DDSB_N'),
        ([1145, 1395, 1205, 1395, 1205, 1320], None),
        ([1205, 1320, 1455, 1320], 'CLK100_LMXA_P'),
        ([1145, 1405, 1220, 1405, 1220, 1345], None),
        ([1220, 1345, 1455, 1345], 'CLK100_LMXA_N'),
        ([1145, 1415, 1235, 1415, 1235, 1370], None),
        ([1235, 1370, 1455, 1370], 'CLK100_LMXB_P'),
        ([1145, 1425, 1250, 1425, 1250, 1395], None),
        ([1250, 1395, 1455, 1395], 'CLK100_LMXB_N'),
        ([1145, 1435, 1265, 1435, 1265, 1420], None),
        ([1265, 1420, 1455, 1420], 'CLK_FB_P'),
        ([1145, 1445, 1455, 1445], 'CLK_FB_N'),
        # U226 Decoupling bus
        ([890, 1155, 890, 1140, 920, 1140], None),
        ([960, 1140, 1310, 1140, 1310, 1155], None),
        ([1030, 1120, 1030, 1140], None),
        ([1110, 1120, 1110, 1140], None),
        ([1190, 1120, 1190, 1140], None),
        ([1270, 1120, 1270, 1140], None),
        ([1030, 1080, 1030, 1060, 1270, 1060, 1270, 1080], None),
        ([1110, 1080, 1110, 1060], None),
        ([1190, 1080, 1190, 1060], None),
        ([1150, 1060, 1150, 1045], None),
        # U226 OUT5 -> R258 (1630,1505 -> pins 1525 & 1485) -> U227 SN65LVDS2 (40u apart!)
        ([1145, 1465, 1220, 1465, 1220, 1525, 1300, 1525], None),
        ([1300, 1525, 1490, 1525], 'CLK100_DIV_N'),
        ([1490, 1525, 1630, 1525], None),
        ([1630, 1525, 1595, 1525, 1595, 1425, 1770, 1425, 1770, 1455, 1750, 1455], None),
        ([1145, 1455, 1235, 1455, 1235, 1485, 1300, 1485], None),
        ([1300, 1485, 1490, 1485], 'CLK100_DIV_P'),
        ([1490, 1485, 1640, 1485, 1640, 1455, 1690, 1455], None),
        ([1690, 1475, 1675, 1475, 1675, 1500, 1715, 1500, 1715, 1515], None),
        ([1690, 1465, 1625, 1465, 1625, 1405, 1645, 1405], None),
        ([1750, 1475, 1855, 1475], 'CLK100_CMOS'),
        ([1855, 1475, 1925, 1475], None),
        # [P1-2] U228 74LVC163PW (D3..D0 = 1011, TC -> U233 -> PE#) + Q2 -> CLK20
        ([1925, 1485, 1895, 1485, 1895, 1525], None),
        ([1925, 1465, 1895, 1465], None),
        ([1925, 1455, 1895, 1455], None),
        ([1925, 1435, 1895, 1435], None),
        ([1925, 1425, 1895, 1425], None),
        ([1895, 1425, 1895, 1485], None),
        ([1925, 1445, 1810, 1445, 1810, 1410], None),
        ([1925, 1415, 1900, 1415, 1900, 1395], None),
        ([1995, 1485, 2025, 1485, 2025, 1505], None),
        ([1995, 1425, 2005, 1425, 2005, 1360, 2025, 1360, 2025, 1370], None),
        ([1995, 1445, 2080, 1445], None),
        ([2080, 1445, 2205, 1445], 'CLK20'),
        ([1995, 1475, 2060, 1475, 2060, u233_a[1], u233_a[0], u233_a[1]], None),
        ([u233_g[0], u233_g[1], 2040, u233_g[1], 2040, 1265], None),
        ([u233_y[0], u233_y[1], 2020, u233_y[1], 2020, 1415, 1995, 1415], None),
        ([u233_v[0], u233_v[1], 1985, u233_v[1]], None),
        # U229 ÷2 -> U230 Buffer -> R260(33Ω) -> C260(DNP) -> J_REFOUT
        ([2205, 1435, 2170, 1435, 2170, 1425, 2205, 1425], None),
        ([2205, 1415, 2185, 1415, 2185, 1395], None),
        ([2275, 1425, 2305, 1425, 2305, 1465], None),
        ([2275, 1435, 2305, 1435], None),
        ([2275, 1445, 2305, 1445], None),
        ([2275, 1415, 2445, 1415], 'CLK10'),
        ([2445, 1405, 2415, 1405, 2415, 1415], None),
        ([2445, 1395, 2375, 1395], None),
        ([2515, 1395, 2540, 1395, 2540, 1375], None),
        ([2515, 1415, 2545, 1415], None),
        ([2545, 1415, r260_l[0], 1415], 'REFOUT_DRV'),
        ([2515, 1405, 2545, 1405, 2545, 1415], None),
        ([r260_r[0], 1415, 2720, 1415], None),
        ([2720, 1415, 2800, 1415], 'REFOUT_BNC'),
        ([c260_t[0], c260_t[1], 2720, 1415], None),
        ([c260_b[0], c260_b[1], 2720, 1315], None),
        ([2820, 1445, 2820, 1455, 2840, 1455, 2840, 1445], None),
        ([2820, 1455, 2780, 1455, 2780, 1450], None),
        ([2820, 1385, 2820, 1375, 2840, 1375, 2840, 1385], None),
        ([2830, 1375, 2830, 1355], None),
        # DIV Decoupling bus C299..C304
        ([1630, 1155, 1630, 1140, 1660, 1140], None),
        ([1700, 1140, 2220, 1140, 2220, 1155], None),
        ([1780, 1120, 1780, 1140], None),
        ([1860, 1120, 1860, 1140], None),
        ([1940, 1120, 1940, 1140], None),
        ([2020, 1120, 2020, 1140], None),
        ([2100, 1120, 2100, 1140], None),
        ([2180, 1120, 2180, 1140], None),
        ([1780, 1080, 1780, 1060, 2180, 1060, 2180, 1080], None),
        ([1860, 1080, 1860, 1060], None),
        ([1940, 1080, 1940, 1060], None),
        ([2020, 1080, 2020, 1060], None),
        ([2100, 1080, 2100, 1060], None),
        ([1980, 1060, 1980, 1045], None),
    ]

    # Preflight graph verify
    if [fl for fl in flags if fl[4] != 0]:
        raise RuntimeError("Non-zero rot flags found on CLK_DIST")
    f_v, rn_v = verify_graph(pg['reals'], flags, ports, wires)
    shorts = []
    for c in pg['reals']:
        for pn, pnm, px, py, _ in c['pins']:
            ns = rn_v.get(f_v((round(px, 1), round(py, 1))), set())
            if len(ns) > 1:
                shorts.append((c['des'], pn, pnm, sorted(ns)))
    if shorts:
        raise RuntimeError(f"CLK_DIST PREFLIGHT SHORTS: {shorts}")
    allowed_nc = {
        ('U225', 'OUT2+'), ('U225', 'OUT2–'), ('U225', 'OUT2-'),
        ('U226', 'IN1_P'), ('U226', 'IN1_N'), ('U226', 'VAC_REF0'), ('U226', 'VAC_REF1'),
        ('U226', 'OUT6_P'), ('U226', 'OUT6_N'), ('U226', 'OUT7_P'), ('U226', 'OUT7_N'),
        ('U228', 'Q0'), ('U228', 'Q1'), ('U228', 'Q3'),
        ('U233', 'N.C'),
    }
    root_pin_cnt = {}
    for c in pg['reals']:
        for _, _, px, py, _ in c['pins']:
            r = f_v((round(px, 1), round(py, 1)))
            root_pin_cnt[r] = root_pin_cnt.get(r, 0) + 1
    floating = []
    for c in pg['reals']:
        for pn, pnm, px, py, _ in c['pins']:
            if (c['des'], str(pnm)) in allowed_nc:
                continue
            r = f_v((round(px, 1), round(py, 1)))
            ns = rn_v.get(r, set())
            if len(ns) == 0 and root_pin_cnt.get(r, 0) < 2:
                floating.append((c['des'], pn, pnm, sorted(ns)))
    if floating:
        raise RuntimeError(f"CLK_DIST PREFLIGHT FLOATING PINS: {floating}")
    # Also verify exact unnamed internal pairs (CLK10_N / U228_TC / U228_LOAD_N)
    assert f_v(pxy('U229', num='3')) == f_v(pxy('U229', num='2')), "CLK10_N Q#->D broken"
    # Check [P0-1], [P0-2], [P1-2], [P2-1], & 6 decap GNDs!
    u226 = {p[1]: f_v((round(p[2], 1), round(p[3], 1))) for p in by_des['U226']['pins']}
    u225 = {p[1]: f_v((round(p[2], 1), round(p[3], 1))) for p in by_des['U225']['pins']}
    u228 = {p[1]: f_v((round(p[2], 1), round(p[3], 1))) for p in by_des['U228']['pins']}
    assert 'CLK_FB_N' in rn_v[u226['OUT4_N']]
    assert 'CLK100_DIV_P' in rn_v[u226['OUT5_P']] and 'CLK100_DIV_N' in rn_v[u226['OUT5_N']]
    assert 'GND' in rn_v[u226['N_SEL']]
    assert 'GND' in rn_v[u225['FILTA']] and 'GND' in rn_v[u225['FILTB']] and 'GND' in rn_v[u225['SD1']] and '3V3_U225' in rn_v[u225['SD2']]
    assert '3V3_DIV' in rn_v[u228['D0']] and '3V3_DIV' in rn_v[u228['D1']] and 'GND' in rn_v[u228['D2']] and '3V3_DIV' in rn_v[u228['D3']]
    assert f_v(pxy('U228', name='TC')) == f_v(u233_a) and f_v(u233_y) == f_v(pxy('U228', name='PE#'))
    for dec in ('C299', 'C300', 'C301', 'C302', 'C303', 'C304'):
        p_roots = [rn_v.get(f_v((round(p[2], 1), round(p[3], 1))), set()) for p in by_des[dec]['pins']]
        assert {'3V3_DIV'} in p_roots and {'GND'} in p_roots, (dec, p_roots)
    print(f"CLK_DIST PREFLIGHT PASSED 100%! wires={len(wires)}, flags={len(flags)}, ports={len(ports)}, shorts=0, P0-1/P0-2/P1-2/P2-1=OK")

    # Apply batches <= 35 (open page once, no repeated openDocument!)
    js(open_page(page_uuid, 600) + "return 1;")
    ops = [('flag', x) for x in flags] + [('port', x) for x in ports] + [('wire', x) for x in wires]
    for idx in range(0, len(ops), 20):
        chunk = ops[idx:idx + 20]
        cf = [x for t, x in chunk if t == 'flag']
        cp = [x for t, x in chunk if t == 'port']
        cw = [x for t, x in chunk if t == 'wire']
        print(f"  CLK_DIST batch {idx // 20 + 1}/{(len(ops) + 19) // 20} ({len(chunk)} items)...")
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
            raise RuntimeError(f"CLK_DIST batch error: {bres}")

    # Boxes & Titles + Save
    js(f"""
await eda.sch_PrimitiveRectangle.create(110, 1660, 590, 700, 0, 0, '#000000', 'none', 1, null, null);
await eda.sch_PrimitiveText.create(135, 1635, '100M正弦整形 (U225 LTC6957-2)', 0, '#000000', null, 18, true, false, false, 1);
await eda.sch_PrimitiveText.create(135, 1000, 'FILTA/FILTB/SD1=GND; SD2=3V3_U225(关OUT2); FB201磁珠隔离', 0, '#555555', null, 10, false, false, false, 1);

await eda.sch_PrimitiveRectangle.create(720, 1660, 780, 700, 0, 0, '#000000', 'none', 1, null, null);
await eda.sch_PrimitiveText.create(745, 1635, '1:8 LVDS时钟扇出 (U226 LMK1D1208)', 0, '#000000', null, 18, true, false, false, 1);
await eda.sch_PrimitiveText.create(745, 1000, 'N_SEL=GND(选IN0); R257=100Ω端接; 已修复[P0-1]OUT4_N与OUT5_P/N完整扇出', 0, '#555555', null, 10, false, false, false, 1);

await eda.sch_PrimitiveRectangle.create(1520, 1660, 1400, 700, 0, 0, '#000000', 'none', 1, null, null);
await eda.sch_PrimitiveText.create(1545, 1635, '10MHz参考分频与驱动输出 (U228+U233 ÷5 → ÷2 → 33Ω 50Ω匹配)', 0, '#000000', null, 18, true, false, false, 1);
await eda.sch_PrimitiveText.create(1545, 1000, '已合入[P0-2] R260=33Ω/C260=100pF(DNP) 与 [P1-2] D3..D0=1011 TC→SN74LVC1G04→PE#', 0, '#555555', null, 10, false, false, false, 1);

await eda.dmt_Schematic.modifySchematicPageName({json.dumps(page_uuid)}, {json.dumps(PAGE_NAME)});
await new Promise(r => setTimeout(r, 250));
await eda.sch_Document.save();
await new Promise(r => setTimeout(r, 800));
return 1;
""")

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
    print(f"CLK_DIST LIVE VERIFY: uuid={page_uuid}, reals={len(pg_fin['reals'])}, flags={len(pg_fin['flags'])}, wires={len(pg_fin['wires'])}, offgrid={offgrid}")
    return page_uuid


if __name__ == '__main__':
    run()
