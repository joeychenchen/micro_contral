# -*- coding: utf-8 -*-
"""Step B-Polish: Rewire 'power' page U304/U305 zone with full orthogonal buses & clean rules."""
import json
import math
import sys

sys.path.insert(0, r'c:\Users\Jo1yc\Desktop\硕士课题\_agent_tmp')
from nvmw_lib import POWER_PAGE_UUID, dump_page, js, open_page


def on_seg_excl(px, py, x0, y0, x1, y1, tol=0.15):
    """True if point (px,py) lies on orthogonal segment (x0,y0)-(x1,y1)."""
    if abs(x0 - x1) < tol and abs(px - x0) < tol:
        return min(y0, y1) - tol <= py <= max(y0, y1) + tol
    if abs(y0 - y1) < tol and abs(py - y0) < tol:
        return min(x0, x1) - tol <= px <= max(x0, x1) + tol
    return False


def union_find_power(pg):
    """T-junction aware union-find over EasyEDA 4-number wire chunks + flags + pins."""
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
        ln = w['line']
        for i in range(0, len(ln) - 2, 2):
            p0 = (round(ln[i], 1), round(ln[i + 1], 1))
            p1 = (round(ln[i + 2], 1), round(ln[i + 3], 1))
            if p0 == p1:
                continue
            segs.append((p0, p1))
            union(p0, p1)
            if w['net']:
                union(p0, ('NET', w['net']))
    for f in pg['flags']:
        pt = (round(f['x'], 1), round(f['y'], 1))
        parent.setdefault(pt, pt)
        if f['net']:
            union(pt, ('NET', f['net']))
    for c in pg['reals']:
        for _, _, px, py, _ in c['pins']:
            pt = (round(px, 1), round(py, 1))
            parent.setdefault(pt, pt)

    # Only vertices/endpoints (NOT perpendicular crossings without vertex!) T-connect to segments
    pts = [k for k in list(parent) if isinstance(k, tuple) and isinstance(k[0], (int, float))]
    for pt in pts:
        for p0, p1 in segs:
            if on_seg_excl(pt[0], pt[1], p0[0], p0[1], p1[0], p1[1]):
                union(pt, p0)

    rnames = {}
    for k in list(parent):
        if isinstance(k, tuple) and k[0] == 'NET':
            rnames.setdefault(find(k), set()).add(k[1])
    return find, rnames


DX = 700
DY = 120


def run():
    pg = dump_page(POWER_PAGE_UUID)
    by_des = {c['des']: c for c in pg['reals']}

    # 1. Collect items in old (x>=490, y<=200) or new (x>=1180) zone + R10/R13 3V3_PLL_LDO flags/wires
    del_wire_pids = []
    for w in pg['wires']:
        xs = w['line'][0::2]
        ys = w['line'][1::2]
        if (max(xs) >= 490 and min(ys) <= 200) or max(xs) >= 1180:
            del_wire_pids.append(w['pid'])
        elif w.get('net') == '3V3_PLL_LDO' and max(xs) <= 230:
            del_wire_pids.append(w['pid'])
        elif (abs(min(xs) - 190) < 2 and max(xs) <= 210) and (
            (min(ys) >= 740 and max(ys) <= 765) or (min(ys) >= 600 and max(ys) <= 625)
        ):
            del_wire_pids.append(w['pid'])

    del_flag_pids = []
    for f in pg['flags']:
        if f.get('ct') == 'sheet':
            continue
        if (f['x'] >= 490 and f['y'] <= 200) or f['x'] >= 1180:
            del_flag_pids.append(f['pid'])
        elif f.get('net') == '3V3_PLL_LDO' and f['x'] <= 230:
            del_flag_pids.append(f['pid'])

    # Rectangles/texts in old or new zone (plus any duplicate U304/U305 title texts)
    extra_meta = js(open_page(POWER_PAGE_UUID, 500) + """
const rs = (await eda.sch_PrimitiveRectangle.getAll()) || [];
const ts = (await eda.sch_PrimitiveText.getAll()) || [];
return {
  rects: rs.map(r => ({pid: r.getState_PrimitiveId(), x: r.getState_TopLeftX(), y: r.getState_TopLeftY()})),
  texts: ts.map(t => {
    let txt = '';
    try { txt = String(t.getState_Content() || ''); } catch(e) {}
    return {pid: t.getState_PrimitiveId(), x: t.getState_X(), y: t.getState_Y(), txt};
  })
};
""")
    del_rect_pids = [r['pid'] for r in extra_meta['rects'] if (r['x'] >= 480 and r['y'] <= 210) or r['x'] >= 1180]
    del_text_pids = [
        t['pid'] for t in extra_meta['texts']
        if (t['x'] >= 480 and t['y'] <= 210) or t['x'] >= 1180 or 'U304' in t['txt'] or '3V3_PLL_LDO' in t['txt']
    ]

    # Simplify names + move U304/C321..C323/U305/C324..C325 cleanly to right of A4 sheet frame (+DX, +DY)
    clean_names = {
        'L5': '68uH', 'L4': '2.2uH', 'L6': '15uH',
        'C27': '22uF', 'C45': '470uF', 'C47': '180uF',
        'U304': 'TPS60403DBVR', 'C321': '1uF', 'C322': '1uF', 'C323': '1uF',
        'U305': 'TLV75733PDBVR', 'C324': '10uF', 'C325': '10uF',
    }
    moves = {
        'U304': (670 + DX, 110 + DY, 0),
        'C321': (535 + DX, 100 + DY, 90),
        'C322': (590 + DX, 100 + DY, 90),
        'C323': (760 + DX, 100 + DY, 90),
        'U305': (970 + DX, 120 + DY, 0),
        'C324': (870 + DX, 100 + DY, 90),
        'C325': (1060 + DX, 100 + DY, 90),
    }
    updates = []
    for des, nm in clean_names.items():
        if des in by_des:
            it = {'pid': by_des[des]['pid'], 'name': nm}
            if des in moves:
                it['x'], it['y'], it['rot'] = moves[des]
            updates.append(it)

    print(f"Deleting wires={len(del_wire_pids)}, flags={len(del_flag_pids)}, rects={len(del_rect_pids)}, texts={len(del_text_pids)}; updating {len(updates)} comps...")
    js(open_page(POWER_PAGE_UUID, 500) + f"""
for (const id of {json.dumps(del_wire_pids)}) await eda.sch_PrimitiveWire.delete(id);
for (const id of {json.dumps(del_flag_pids)}) await eda.sch_PrimitiveComponent.delete(id);
for (const id of {json.dumps(del_rect_pids)}) await eda.sch_PrimitiveRectangle.delete(id);
for (const id of {json.dumps(del_text_pids)}) await eda.sch_PrimitiveText.delete(id);
for (const u of {json.dumps(updates)}) {{
  const c = await eda.sch_PrimitiveComponent.get(u.pid);
  if (!c) continue;
  const a = c.toAsync();
  a.setState_Name(u.name);
  a.setState_AddIntoBom(true);
  a.setState_AddIntoPcb(true);
  if (u.x !== undefined) {{ a.setState_X(u.x); a.setState_Y(u.y); a.setState_Rotation(u.rot); }}
  await a.done();
}}
await new Promise(r => setTimeout(r, 250));
return 1;
""", timeout=180)

    # Read actual live pins after moving!
    pg2 = dump_page(POWER_PAGE_UUID)
    by2 = {c['des']: c for c in pg2['reals']}
    for des in ('U304', 'C321', 'C322', 'C323', 'U305', 'C324', 'C325'):
        print(f"  {des} @{by2[des]['x']},{by2[des]['y']}: {[(p[0],p[1],round(p[2],1),round(p[3],1)) for p in by2[des]['pins']]}")

    def pxy(des, match=None):
        for pn, pnm, px, py, _ in by2[des]['pins']:
            if match is None or str(pnm).upper() == match.upper() or str(pn) == str(match):
                return round(px, 1), round(py, 1)
        raise KeyError((des, match))

    def top_bot(des):
        p1 = by2[des]['pins'][0]
        p2 = by2[des]['pins'][1]
        a, b = (round(p1[2], 1), round(p1[3], 1)), (round(p2[2], 1), round(p2[3], 1))
        return (a, b) if a[1] > b[1] else (b, a)  # +Y is UP

    c321_t, c321_b = top_bot('C321')
    c322_t, c322_b = top_bot('C322')
    c323_t, c323_b = top_bot('C323')
    c324_t, c324_b = top_bot('C324')
    c325_t, c325_b = top_bot('C325')

    u304_in = pxy('U304', 'IN')
    u304_cp = pxy('U304', 'CFLY+')
    u304_cm = pxy('U304', 'CFLY-')
    u304_gnd = pxy('U304', 'GND')
    u304_out = pxy('U304', 'OUT')

    u305_in = pxy('U305', 'IN')
    u305_gnd = pxy('U305', 'GND')
    u305_en = pxy('U305', 'EN')
    u305_out = pxy('U305', 'OUT')

    # Full direct orthogonal polylines (pass null net for all Power & GND wires -> zero double labels!)
    flags = [
        # R10 & R13 vertical Power rot=0 pointing UP
        ('Power', '3V3_PLL_LDO', 200, 760, 0),
        ('Power', '3V3_PLL_LDO', 200, 620, 0),
        # U304 block: VCC_5V UP (rot=0), VEE_N5V UP (rot=0), GND DOWN (rot=0)
        ('Power', 'VCC_5V', c321_t[0], 155 + DY, 0),
        ('Power', 'VEE_N5V', c323_t[0], 155 + DY, 0),
        ('Ground', 'GND', 670 + DX, 45 + DY, 0),
        # U305 block: VCC_5V UP (rot=0), 3V3_PLL_LDO UP (rot=0), GND DOWN (rot=0)
        ('Power', 'VCC_5V', c324_t[0], 155 + DY, 0),
        ('Power', '3V3_PLL_LDO', c325_t[0], 155 + DY, 0),
        ('Ground', 'GND', 970 + DX, 45 + DY, 0),
    ]

    # Note: EasyEDA create(poly, null) accepts continuous multi-point orthogonal polylines cleanly
    wires = [
        # R10 & R13 -> 3V3_PLL_LDO flags (power wire -> net=None)
        ([190, 745, 200, 745, 200, 760], None),
        ([190, 605, 200, 605, 200, 620], None),
        # U304 VCC_5V bus & C321
        ([c321_t[0], 155 + DY, c321_t[0], c321_t[1]], None),
        ([c321_t[0], u304_in[1], u304_in[0], u304_in[1]], None),
        # U304 C322 flying cap DIRECT orthogonal traces (no island NetPorts!)
        ([c322_t[0], c322_t[1], u304_cp[0], u304_cp[1]], None),
        ([c322_b[0], c322_b[1], 605 + DX, c322_b[1], 605 + DX, u304_cm[1], u304_cm[0], u304_cm[1]], None),
        # U304 VEE_N5V bus & C323
        ([c323_t[0], 155 + DY, c323_t[0], c323_t[1]], None),
        ([u304_out[0], u304_out[1], c323_t[0], u304_out[1]], None),
        # U304 GND bus (explicit non-collinear branches meeting at (670+DX, 60+DY) -> GND@670+DX,45+DY)
        ([c321_b[0], c321_b[1], c321_b[0], 60 + DY, 670 + DX, 60 + DY], None),
        ([c323_b[0], c323_b[1], c323_b[0], 60 + DY, 670 + DX, 60 + DY], None),
        ([u304_gnd[0], u304_gnd[1], 670 + DX, 60 + DY], None),
        ([670 + DX, 60 + DY, 670 + DX, 45 + DY], None),

        # U305 VCC_5V bus & C324 (orthogonal cross at (915+DX, 110+DY) has no vertex)
        ([c324_t[0], 155 + DY, c324_t[0], c324_t[1]], None),
        ([c324_t[0], 140 + DY, 915 + DX, 140 + DY, 915 + DX, u305_in[1], u305_in[0], u305_in[1]], None),
        ([895 + DX, 140 + DY, 895 + DX, u305_en[1], u305_en[0], u305_en[1]], None),
        # U305 GND bus (shared C324, U305.GND, C325 -> GND@970+DX,45+DY)
        ([c324_b[0], c324_b[1], c324_b[0], 60 + DY, c325_b[0], 60 + DY, c325_b[0], c325_b[1]], None),
        ([u305_gnd[0], u305_gnd[1], 915 + DX, u305_gnd[1], 915 + DX, 60 + DY], None),
        ([970 + DX, 60 + DY, 970 + DX, 45 + DY], None),
        # U305 3V3_PLL_LDO bus & C325
        ([c325_t[0], 155 + DY, c325_t[0], c325_t[1]], None),
        ([u305_out[0], u305_out[1], 1025 + DX, u305_out[1], 1025 + DX, 140 + DY, c325_t[0], 140 + DY], None),
    ]

    js(open_page(POWER_PAGE_UUID, 400) + f"""
for (const [kind, net, x, y, rot] of {json.dumps(flags)}) {{
  await eda.sch_PrimitiveComponent.createNetFlag(kind, net, x, y, rot, false);
}}
for (const [line, net] of {json.dumps(wires)}) {{
  await (net ? eda.sch_PrimitiveWire.create(line, net) : eda.sch_PrimitiveWire.create(line));
}}
await eda.sch_PrimitiveRectangle.create({495 + DX}, {200 + DY}, 625, 175, 0, 0, '#000000', 'none', 1, null, null);
await eda.sch_PrimitiveText.create({510 + DX}, {185 + DY}, '新增模拟负压 (-5V U304) 与 LMX2595 专用线性 LDO (1A U305 3V3_PLL_LDO)', 0, '#000000', null, 12, true, false, false, 1);
await new Promise(r => setTimeout(r, 250));
await eda.sch_Document.save();
await new Promise(r => setTimeout(r, 600));
return 1;
""", timeout=180)

    # Read-back & T-junction union-find verification
    pg_fin = dump_page(POWER_PAGE_UUID)
    find, rnames = union_find_power(pg_fin)
    for des in ('U304', 'C321', 'C322', 'C323', 'U305', 'C324', 'C325', 'R10', 'R13'):
        c = [x for x in pg_fin['reals'] if x['des'] == des][0]
        pns = [(pn, pnm, sorted(rnames.get(find((round(px, 1), round(py, 1))), set()))) for pn, pnm, px, py, _ in c['pins']]
        print(f"  VERIFY {des:5s}: {pns}")
    bad_rot = [(f['net'], f['rot']) for f in pg_fin['flags'] if f['x'] >= 1180 and f['rot'] != 0]
    new_wnets = [w['net'] for w in pg_fin['wires'] if max(w['line'][0::2]) >= 1180 and w['net']]
    print("Non-zero rot flags in new zone:", bad_rot, "| Wire net labels in new power zone:", new_wnets)
    # Check C322 top/bot joined to U304 CFLY+ / CFLY-
    u304_fin = [x for x in pg_fin['reals'] if x['des'] == 'U304'][0]
    c322_fin = [x for x in pg_fin['reals'] if x['des'] == 'C322'][0]
    p_map = {p[1]: find((round(p[2], 1), round(p[3], 1))) for p in u304_fin['pins']}
    c_roots = [find((round(p[2], 1), round(p[3], 1))) for p in c322_fin['pins']]
    print("C322 connected to U304 CFLY+ & CFLY- directly?:", set(c_roots) == {p_map['CFLY+'], p_map['CFLY-']}, "| distinct roots:", len(set(p_map.values())) == 5)


if __name__ == '__main__':
    run()
