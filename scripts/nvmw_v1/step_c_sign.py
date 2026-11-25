# -*- coding: utf-8 -*-
"""Step C Phase 1-3: Clean obsolete blocks, fix mid bugs, place new AM VVA + LVDS + MCU Header H1 on 'sign'."""
import json
import sys

sys.path.insert(0, r'c:\Users\Jo1yc\Desktop\硕士课题\_agent_tmp')
from nvmw_lib import DEVS, SIGN_PAGE_UUID, dump_page, js, open_page

NEW_DES_SET = {
    'R310', 'R300', 'R309',
    'U301', 'U302', 'U303', 'D301', 'J_RFOUT', 'H1',
    'C311', 'C312', 'C313', 'C314', 'C315', 'C316', 'C317', 'C318', 'C319', 'C320',
    'R301', 'R302', 'R303', 'R304', 'R305', 'R306', 'R307', 'R308',
}


def run_place():
    pg = dump_page(SIGN_PAGE_UUID)
    print(f"Live sign before Phase 1: reals={len(pg['reals'])}, flags={len(pg['flags'])}, wires={len(pg['wires'])}")

    # Detect whether old clk/pa cleanup is still needed
    has_old = any(c['x'] < -100 or (c['x'] > 1700 and c['des'] not in NEW_DES_SET) for c in pg['reals'])
    if has_old:
        del_comp_pids = []
        del_wire_pids = []
        del_rect_pids = []
        del_text_pids = []

        # Comps to delete: clk_old (x < -100), pa_old (x > 1700), R58, R59, R15, R17
        for c in pg['reals']:
            if c['x'] < -100 or (c['x'] > 1700 and c['des'] not in NEW_DES_SET) or c['des'] in ('R58', 'R59', 'R15', 'R17'):
                del_comp_pids.append(c['pid'])

        # Flags to delete: x < -100, x > 1700, R15/R17 GND, U2.39 off-grid GND, C58.1/mid AGND (to replace)
        create_flags = []
        for f in pg['flags']:
            if f.get('ct') == 'sheet':
                continue
            x, y, net = f['x'], f['y'], f.get('net')
            if x < -100 or x > 1700:
                del_comp_pids.append(f['pid'])
            elif f['pid'] in ('546b9d54547e7d1a', 'c1304197ebd32fad', 'd3b21ebd49897ce3'):
                del_comp_pids.append(f['pid'])
            elif abs(x - 435) < 2 and abs(y - 80) < 2 and net == 'GND':
                del_comp_pids.append(f['pid'])
            elif abs(x - 485) < 2 and abs(y - 60) < 2 and net == 'GND':
                del_comp_pids.append(f['pid'])
            elif abs(x - 798.99) < 3 and abs(y - 195.12) < 3 and net == 'GND':
                del_comp_pids.append(f['pid'])
            elif net == 'AGND' and -100 <= x <= 1700:
                del_comp_pids.append(f['pid'])
                # Keep replacing the 2 mid AGND flags (0,390) & (250,510), drop C58.1 AGND @(265,680)
                if not (abs(x - 265) < 2 and abs(y - 680) < 2):
                    create_flags.append({'kind': 'Ground', 'net': 'GND', 'x': x, 'y': y, 'rot': f['rot']})

        # Add aligned GND flag for U2.39
        create_flags.append({'kind': 'Ground', 'net': 'GND', 'x': 795, 'y': 195, 'rot': 0})

        # Wires to delete
        mid_del_wire_pids = {
            '83aa0e6788771172', 'aeec8f80dbed8425', '5299799706e614c1', 'aabaef57fda37e83',
            'e98e867c58c30db1', '18eca74f226ae7de',
            'f004e82ec1da9e8d', '05da823bf4051819', '3fe90b0c147eb0a2', 'a1b4d7579610c03a',
            'ee1225c63d240743',
        }
        for w in pg['wires']:
            xs = w['line'][0::2]
            if min(xs) < -100 or max(xs) > 1700 or w['pid'] in mid_del_wire_pids:
                del_wire_pids.append(w['pid'])

        # Recreated fixed mid wires
        create_wires = [
            # U2.10 (VregIN)
            {'line': [590, 105, 615, 105], 'net': 'VregIN'},
            # U2.14 & U2.13 (GND)
            {'line': [615, 75, 610, 75], 'net': 'GND'},
            {'line': [615, 65, 610, 65], 'net': 'GND'},
            {'line': [610, 65, 610, 75], 'net': 'GND'},
            {'line': [605, 70, 610, 70], 'net': 'GND'},
            # U2.39 & U2.40 (GND)
            {'line': [775, 195, 795, 195], 'net': 'GND'},
            {'line': [775, 185, 780, 185], 'net': 'GND'},
            {'line': [780, 185, 780, 195], 'net': 'GND'},
            # U5.22 (*REF_CLK) <-> C58.2
            {'line': [315, 680, 320, 680], 'net': ''},
            # U14.1 (DSOP) <-> R57.1 & NetPort ADL5375_DSOP
            {'line': [1355, 355, 1375, 355], 'net': 'ADL5375_DSOP'},
        ]

        # Old clock & PA texts
        for t in pg['texts']:
            if t['x'] < -100 or t['x'] > 1700:
                del_text_pids.append(t['pid'])

        # Fetch rect coords dynamically to delete clock/PA boxes cleanly
        rect_list = js(open_page(SIGN_PAGE_UUID, 500) + """
const rs = (await eda.sch_PrimitiveRectangle.getAll()) || [];
return rs.map(r => ({pid: r.getState_PrimitiveId(), x: r.getState_TopLeftX()}));
""")
        del_rect_pids = [r['pid'] for r in rect_list if r['x'] < -100 or r['x'] > 1700]

        print(f"Phase 1 deleting: wires={len(del_wire_pids)}, comps/flags={len(del_comp_pids)}, rects={len(del_rect_pids)}, texts={len(del_text_pids)}")
        js(open_page(SIGN_PAGE_UUID, 500) + f"""
if ({json.dumps(del_wire_pids)}.length) await eda.sch_PrimitiveWire.delete({json.dumps(del_wire_pids)});
if ({json.dumps(del_comp_pids)}.length) await eda.sch_PrimitiveComponent.delete({json.dumps(del_comp_pids)});
if ({json.dumps(del_rect_pids)}.length) await eda.sch_PrimitiveRectangle.delete({json.dumps(del_rect_pids)});
if ({json.dumps(del_text_pids)}.length) await eda.sch_PrimitiveText.delete({json.dumps(del_text_pids)});
for (const fl of {json.dumps(create_flags)}) {{
  await eda.sch_PrimitiveComponent.createNetFlag(fl.kind, fl.net, fl.x, fl.y, fl.rot, false);
}}
for (const wr of {json.dumps(create_wires)}) {{
  await eda.sch_PrimitiveWire.create(wr.line, wr.net || undefined);
}}
await new Promise(r => setTimeout(r, 300));
await eda.sch_Document.save();
return 1;
""", timeout=180)
        print("Phase 1 cleanup & mid fixes saved.")

    # Phase 2 & 3: Check existing components & place missing new components in <=10 batches
    pg = dump_page(SIGN_PAGE_UUID)
    existing_des = {c['des'] for c in pg['reals']}
    u303_units = sum(1 for c in pg['reals'] if c['des'] == 'U303')

    specs = [
        # Batch 1: LVDS/SYNC resistors + Core AM ICs + Connectors + Header (10 instances)
        ('R310', DEVS['R100R_0402'], 425, 115, 90, '100Ω', None),
        ('R300', DEVS['R100R_0402'], 210, 615, 90, '100Ω', None),
        ('R309', DEVS['R10K_0603'], 290, 520, 0, '10kΩ', None),
        ('U301', DEVS['HMC346AMS8GETR'], 2420, 220, 0, 'HMC346AMS8GETR', None),
        ('U302', DEVS['DAC8551IDGKR'], 1900, 180, 0, 'DAC8551IDGKR', None),
        ('U303', DEVS['OPA2192IDR'], 2160, 180, 0, 'OPA2192IDR-A', 'OPA2192IDR.1'),
        ('U303', DEVS['OPA2192IDR'], 2160, 440, 0, 'OPA2192IDR-B', 'OPA2192IDR.2'),
        ('D301', DEVS['BAV99'], 2400, 470, 0, 'BAV99', None),
        ('J_RFOUT', DEVS['SMA_KE_5'], 2620, 310, 180, 'RF_OUT SMA', None),
        ('H1', DEVS['HDR_2X20P'], 1980, 880, 0, 'STM32H7_2x20P', None),
        # Batch 2: AM decoupling & RF coupling caps (10 parts)
        ('C311', DEVS['C100P_0402'], 2310, 280, 0, '100pF', None),
        ('C312', DEVS['C100P_0402'], 2530, 310, 0, '100pF', None),
        ('C313', DEVS['C100N_0603'], 1820, 290, 90, '100nF', None),
        ('C314', DEVS['C1U_0603'], 1880, 290, 90, '1uF', None),
        ('C315', DEVS['C100N_0603'], 2090, 290, 90, '100nF', None),
        ('C320', DEVS['C100N_0603'], 2210, 290, 90, '100nF', None),
        ('C316', DEVS['C100P_0603'], 2160, 60, 0, '100pF', None),
        ('C317', DEVS['C1N_0603'], 2160, 360, 0, '1nF', None),
        ('C318', DEVS['C100P_0603'], 2320, 210, 90, '100pF', None),
        ('C319', DEVS['C100P_0603'], 2320, 470, 90, '100pF', None),
        # Batch 3: AM resistors (8 parts)
        ('R301', DEVS['R10K_0603'], 2050, 120, 0, '10kΩ', None),
        ('R302', DEVS['R10K_0603'], 2160, 100, 0, '10kΩ', None),
        ('R303', DEVS['R510R_0603'], 1900, 490, 90, '510Ω (510Ω/600Ω可调)', None),
        ('R304', DEVS['R10K_0603'], 1900, 400, 90, '10kΩ', None),
        ('R305', DEVS['R10K_0603'], 1990, 440, 90, '10kΩ', None),
        ('R306', DEVS['R1K_0603'], 2260, 440, 0, '1kΩ', None),
        ('R307', DEVS['R1K_0603'], 2260, 180, 0, '1kΩ', None),
        ('R308', DEVS['R10K_0603'], 1960, 290, 90, '10kΩ', None),
    ]

    # Filter out already placed
    to_run = []
    seen_u303 = u303_units
    for des, dev, x, y, rot, name, sub in specs:
        if des == 'U303':
            if seen_u303 >= 2:
                continue
            if seen_u303 == 1 and sub == 'OPA2192IDR.1':
                continue
        elif des in existing_des:
            continue
        fb = DEVS['HDR_2X20P_SYS'] if des == 'H1' else dev
        to_run.append({
            'des': des, 'lib1': dev[0], 'uuid1': dev[1],
            'lib2': fb[0], 'uuid2': fb[1],
            'x': x, 'y': y, 'rot': rot, 'name': name, 'sub': sub,
        })

    for idx in range(0, len(to_run), 10):
        chunk = to_run[idx:idx + 10]
        print(f"Placing chunk {idx // 10 + 1} ({[c['des'] + ('.' + c['sub'][-1] if c['sub'] else '') for c in chunk]})...")
        res = js(open_page(SIGN_PAGE_UUID, 500) + f"""
const items = {json.dumps(chunk, ensure_ascii=False)};
const placed = [], failed = [];
for (const it of items) {{
  let c = null;
  try {{
    c = await eda.sch_PrimitiveComponent.create({{libraryUuid: it.lib1, uuid: it.uuid1}}, it.x, it.y, it.sub || undefined, it.rot, false, false, false);
  }} catch(e) {{}}
  if (!c && (it.lib2 !== it.lib1 || it.uuid2 !== it.uuid1)) {{
    try {{
      c = await eda.sch_PrimitiveComponent.create({{libraryUuid: it.lib2, uuid: it.uuid2}}, it.x, it.y, it.sub || undefined, it.rot, false, false, false);
    }} catch(e) {{}}
  }}
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
        print('  result:', res)
        if res['failed']:
            raise RuntimeError(f"sign placement failed: {res['failed']}")

    # Inspect actual pins of newly placed components
    pg_fin = dump_page(SIGN_PAGE_UUID)
    placed_info = [c for c in pg_fin['reals'] if c['des'] in NEW_DES_SET]
    json.dump(placed_info, open(r'c:\Users\Jo1yc\Desktop\硕士课题\_agent_tmp\sign_placed_pins.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
    print(f"Saved {len(placed_info)} placed component instances on sign (reals total={len(pg_fin['reals'])})")
    for c in placed_info:
        if c['des'] in ('R310', 'R300', 'R309', 'U301', 'U302', 'U303', 'D301', 'J_RFOUT', 'H1'):
            ps = c['pins']
            pstr = str(ps) if len(ps) <= 10 else f"{len(ps)} pins sample: {ps[:4]}"
            print(f"  {c['des']} sub={c['sub']} @{c['x']},{c['y']} pins={pstr}")


if __name__ == '__main__':
    run_place()
