# -*- coding: utf-8 -*-
"""Read-only 5-page EasyEDA Pro geometric, BBox, and label audit for NVmw (exact 4-number wire chunks).

NEVER calls eda.sch_Netlist.getNetlist() or getNetlistFile().
"""
import json
import math
import sys

sys.path.insert(0, r'c:\Users\Jo1yc\Desktop\硕士课题\_agent_tmp')
from nvmw_lib import dump_page, get_pages, js, open_page


def iter_wire_segs(ln):
    """Yield (x0, y0, x1, y1) from EasyEDA w['line'] (4-number segment list)."""
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


def on_seg(px, py, x0, y0, x1, y1, tol=0.25):
    if abs(x0 - x1) < tol and abs(px - x0) < tol:
        return min(y0, y1) - tol <= py <= max(y0, y1) + tol
    if abs(y0 - y1) < tol and abs(py - y0) < tol:
        return min(x0, x1) - tol <= px <= max(x0, x1) + tol
    return False


def seg_intersects_bbox_interior(x0, y0, x1, y1, bb, anchors):
    if not bb:
        return False
    minx, maxx = bb['minX'] + 0.5, bb['maxX'] - 0.5
    miny, maxy = bb['minY'] + 0.5, bb['maxY'] - 0.5
    if minx >= maxx or miny >= maxy:
        return False
    s_minx, s_maxx = min(x0, x1), max(x0, x1)
    s_miny, s_maxy = min(y0, y1), max(y0, y1)
    if s_maxx <= minx or s_minx >= maxx or s_maxy <= miny or s_miny >= maxy:
        return False
    cx0, cx1 = max(s_minx, minx), min(s_maxx, maxx)
    cy0, cy1 = max(s_miny, miny), min(s_maxy, maxy)
    for px, py in [(cx0, cy0), ((cx0 + cx1) / 2.0, (cy0 + cy1) / 2.0), (cx1, cy1)]:
        if not anchors or min(math.hypot(px - ax, py - ay) for ax, ay in anchors) > 2.5:
            return True
    return False


def build_conn_components(pg):
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
        for x0, y0, x1, y1 in iter_wire_segs(w['line']):
            p0 = (round(x0, 1), round(y0, 1))
            p1 = (round(x1, 1), round(y1, 1))
            segs.append((w['pid'], w['net'] or '', p0, p1))
            union(p0, p1)
    for f in pg['flags']:
        pt = (round(f['x'], 1), round(f['y'], 1))
        parent.setdefault(pt, pt)
    for c in pg['reals']:
        for _, _, px, py, _ in c['pins']:
            parent.setdefault((round(px, 1), round(py, 1)), (round(px, 1), round(py, 1)))
    pts = [k for k in list(parent) if isinstance(k, tuple)]
    for pt in pts:
        for _, _, p0, p1 in segs:
            if on_seg(pt[0], pt[1], p0[0], p0[1], p1[0], p1[1]):
                union(pt, p0)
    return find, segs


def probe_bboxes(page_uuid):
    return js(open_page(page_uuid, 600) + """
const comps = (await eda.sch_PrimitiveComponent.getAll()) || [];
const out = {flags: [], reals: []};
for (const c of comps) {
  const ct = String(c.getState_ComponentType ? c.getState_ComponentType() : '');
  if (ct === 'sheet') continue;
  const pid = c.getState_PrimitiveId();
  let bb = null;
  try {
    const res = await eda.sch_Primitive.getPrimitivesBBox([pid]);
    bb = Array.isArray(res) ? res[0] : res;
  } catch(e) {}
  const des = c.getState_Designator ? c.getState_Designator() : null;
  if (!des) {
    const op = c.getState_OtherProperty ? c.getState_OtherProperty() : null;
    out.flags.push({
      pid, ct, net: c.getState_Net ? c.getState_Net() : '',
      x: c.getState_X(), y: c.getState_Y(), rot: c.getState_Rotation(),
      desc: op ? op.Description : null, bb
    });
  } else {
    out.reals.push({pid, des, x: c.getState_X(), y: c.getState_Y(), rot: c.getState_Rotation(), bb});
  }
}
return out;
""", timeout=120)


def main():
    pages = get_pages()
    full = {}
    for p in pages:
        pname, pid = p['name'], p['uuid']
        pg = dump_page(pid)
        bb_info = probe_bboxes(pid)
        find, segs = build_conn_components(pg)

        col_overlaps = []
        col_nearmiss = []
        near_parallel = []
        for i in range(len(segs)):
            pid1, net1, a0, a1 = segs[i]
            r1 = find(a0)
            for j in range(i + 1, len(segs)):
                pid2, net2, b0, b1 = segs[j]
                r2 = find(b0)
                if abs(a0[0] - a1[0]) < 0.25 and abs(b0[0] - b1[0]) < 0.25:
                    alo, ahi = min(a0[1], a1[1]), max(a0[1], a1[1])
                    blo, bhi = min(b0[1], b1[1]), max(b0[1], b1[1])
                    ov = min(ahi, bhi) - max(alo, blo)
                    dx = abs(a0[0] - b0[0])
                    if dx < 0.25:
                        if pid1 != pid2 and ov > 0.25:
                            col_overlaps.append(('V', a0[0], round(ov, 1), net1, (alo, ahi), net2, (blo, bhi), r1 == r2))
                        elif r1 != r2 and max(blo - ahi, alo - bhi) < 15.0:
                            col_nearmiss.append(('V', a0[0], round(max(blo - ahi, alo - bhi), 1), net1, (alo, ahi), net2, (blo, bhi)))
                    elif r1 != r2 and dx <= 5.5 and ov > 0.25:
                        near_parallel.append(('V', round(dx, 1), a0[0], b0[0], (max(alo, blo), min(ahi, bhi)), net1, net2))
                elif abs(a0[1] - a1[1]) < 0.25 and abs(b0[1] - b1[1]) < 0.25:
                    alo, ahi = min(a0[0], a1[0]), max(a0[0], a1[0])
                    blo, bhi = min(b0[0], b1[0]), max(b0[0], b1[0])
                    ov = min(ahi, bhi) - max(alo, blo)
                    dy = abs(a0[1] - b0[1])
                    if dy < 0.25:
                        if pid1 != pid2 and ov > 0.25:
                            col_overlaps.append(('H', a0[1], round(ov, 1), net1, (alo, ahi), net2, (blo, bhi), r1 == r2))
                        elif r1 != r2 and max(blo - ahi, alo - bhi) < 15.0:
                            col_nearmiss.append(('H', a0[1], round(max(blo - ahi, alo - bhi), 1), net1, (alo, ahi), net2, (blo, bhi)))
                    elif r1 != r2 and dy <= 5.5 and ov > 0.25:
                        near_parallel.append(('H', round(dy, 1), a0[1], b0[1], (max(alo, blo), min(ahi, bhi)), net1, net2))

        bb_pierce_flags = []
        for fl in bb_info['flags']:
            bb = fl['bb']
            if not bb:
                continue
            anchor = [(round(fl['x'], 1), round(fl['y'], 1))]
            for wpid, wnet, p0, p1 in segs:
                if seg_intersects_bbox_interior(p0[0], p0[1], p1[0], p1[1], bb, anchor):
                    bb_pierce_flags.append((fl['ct'], fl['desc'], fl['net'], (fl['x'], fl['y']), fl['rot'], bb, (p0, p1)))

        real_pins_by_des = {c['des']: [(round(p[2], 1), round(p[3], 1)) for p in c['pins']] for c in pg['reals']}
        bb_pierce_reals = []
        for rc in bb_info['reals']:
            bb = rc['bb']
            if not bb:
                continue
            pins = real_pins_by_des.get(rc['des'], [(rc['x'], rc['y'])])
            for wpid, wnet, p0, p1 in segs:
                if seg_intersects_bbox_interior(p0[0], p0[1], p1[0], p1[1], bb, pins):
                    bb_pierce_reals.append((rc['des'], (rc['x'], rc['y']), bb, (p0, p1)))

        wires_with_net = [w for w in pg['wires'] if (w['net'] or '').strip()]
        root_wire_labels = {}
        for w in wires_with_net:
            for x0, y0, x1, y1 in iter_wire_segs(w['line']):
                r = find((round(x0, 1), round(y0, 1)))
                root_wire_labels.setdefault(r, []).append((w['net'], (x0, y0, x1, y1)))
                break

        port_issues = []
        for fl in bb_info['flags']:
            if fl['ct'] != 'netport':
                continue
            r = find((round(fl['x'], 1), round(fl['y'], 1)))
            wn = root_wire_labels.get(r, [])
            is_in = (fl['desc'] == 'Netport-IN')
            if is_in and wn:
                port_issues.append(('IN_HAS_DUPLICATE_WIRE_NET', fl['net'], fl['rot'], (fl['x'], fl['y']), len(wn)))
            elif not is_in and not wn:
                port_issues.append(('OUT_BI_NO_WIRE_NET', fl['desc'], fl['net'], fl['rot'], (fl['x'], fl['y'])))

        crowded_labels = []
        for w in wires_with_net:
            for x0, y0, x1, y1 in iter_wire_segs(w['line']):
                if abs(x0 - x1) < 0.25:
                    crowded_labels.append(('VERT_NET', w['net'], (x0, y0, x1, y1)))
                elif abs(y0 - y1) < 0.25:
                    length = abs(x1 - x0)
                    alo, ahi = min(x0, x1), max(x0, x1)
                    near_wires = []
                    for _, _, p0, p1 in segs:
                        if abs(p0[1] - p1[1]) < 0.25:
                            blo, bhi = min(p0[0], p1[0]), max(p0[0], p1[0])
                            if min(ahi, bhi) > max(alo, blo) and 0.2 < abs(p0[1] - y0) < 15.0:
                                near_wires.append((round(p0[1] - y0, 1), (p0, p1)))
                    if length < 50 or near_wires:
                        crowded_labels.append(('H_CROWD', w['net'], round(length, 1), (x0, y0, x1, y1), near_wires[:3]))

        print(f"\n=== {pname} ===")
        print(f"  col_overlaps={len(col_overlaps)} col_nearmiss={len(col_nearmiss)} near_parallel(<=5.5u)={len(near_parallel)}")
        for x in col_overlaps: print("    OV:", x)
        for x in col_nearmiss: print("    NM:", x)
        for x in near_parallel: print("    NP:", x)
        print(f"  bb_pierce_flags={len(bb_pierce_flags)} bb_pierce_reals={len(bb_pierce_reals)}")
        for x in bb_pierce_flags: print("    PF:", x)
        for x in bb_pierce_reals: print("    PR:", x)
        print(f"  port_issues={len(port_issues)} crowded_labels={len(crowded_labels)}")
        for x in port_issues: print("    PL:", x)
        for x in crowded_labels[:25]: print("    CL:", x)

        full[pname] = {
            'col_overlaps': col_overlaps, 'col_nearmiss': col_nearmiss, 'near_parallel': near_parallel,
            'bb_pierce_flags': bb_pierce_flags, 'bb_pierce_reals': bb_pierce_reals,
            'port_issues': port_issues, 'crowded_labels': crowded_labels,
        }
    json.dump(full, open(r'c:\Users\Jo1yc\Desktop\硕士课题\_agent_tmp\audit_geometry_before.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=2)


if __name__ == '__main__':
    main()
