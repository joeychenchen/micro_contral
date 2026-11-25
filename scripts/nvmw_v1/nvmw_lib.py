# -*- coding: utf-8 -*-
"""Shared helper module for NVmw schematic refactoring via EasyEDA Pro Python bridge."""
import json
import urllib.error
import urllib.request

BRIDGE_URL = 'http://127.0.0.1:49620/execute'
_NO_PROXY_OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}))

PROJECT_UUID = '87f9d2cc03d32aba336dfb63b09e65212d216eb3e947427a284c1d19ae424344'
SCHEMATIC_UUID = '29335980919d6f2e'
SIGN_PAGE_UUID = '46bb8782cca161a7'
POWER_PAGE_UUID = '8e5dfe344ace822c'
PA_PAGE_UUID = 'fb73bcdb610f234c'

SYS_LIB = '0819f05c4eef4c71ace90d822a990e87'
PROJ_LIB = PROJECT_UUID

# Verified device registry (lib, uuid, display_name)
DEVS = {
    # Project-lib PA & common passives (with SYS_LIB online fallbacks where available)
    'PMA3_43_1W': (PROJ_LIB, '4a278fca660e1661', 'PMA3-43-1W+'),
    'PMA3_43_1W_SYS': (SYS_LIB, 'bbc3cdef11904741b5c677a30482ed22', 'PMA3-43-1W+'),
    'HMC1119': (PROJ_LIB, '7d0a0f4b353a9eb6', 'HMC1119LP4METR'),
    'HMC1119_SYS': (SYS_LIB, '30d6b58df969484396f986043d46296b', 'HMC1119LP4METR'),
    'CAP_0603_PROJ': (PROJ_LIB, 'b94eb07e61dc127d', 'CAP_0603'),
    'RES_0603_PROJ': (PROJ_LIB, '812c523b6ba5bafe', 'Res_0603'),
    'L_0603_PROJ': (PROJ_LIB, '2878254949d2bb95', 'L_0603'),
    # Power / LDO / Charge Pump / Inductors / Caps
    'SWPA6045S680MT': (SYS_LIB, '2507e55c358c4e8fa2565b2482d5760f', '68uH'),
    'SWPA4030S2R2MT': (SYS_LIB, '442cb84bf92545da9be5e7fa07a93329', '2.2uH'),
    'SWPA4030S150MT': (SYS_LIB, '8566b52e99784cd0abff922a86a84fc6', '15uH'),
    'C22U_0805': (SYS_LIB, '159c3da60be9490abf4e97599788a0d5', '22uF'),
    'JVJ35V470M10x10': (PROJ_LIB, 'fbec9b9d59e45eee', '470uF'),
    'RVT25V180M6X8': (PROJ_LIB, '8d0bfb46d7409652', '180uF'),
    'TPS60403DBVR': (SYS_LIB, 'e9a478e780f6498e919c5172cb6d1a96', 'TPS60403DBVR'),
    'TLV75733PDBVR': (PROJ_LIB, 'a1e21d1b6e9b2604', 'TLV75733PDBVR'),
    'AMS1117_3V3_PROJ': (PROJ_LIB, 'ca33694f058957fe', 'AMS1117-3.3'),
    # Analog AM + Connector + Header
    'HMC346AMS8GETR': (SYS_LIB, 'b7aed573eb4f48338baff6b678ac3b8c', 'HMC346AMS8GETR'),
    'DAC8551IDGKR': (SYS_LIB, 'f0d74c8d13b0456ea4a45f6da2821d14', 'DAC8551IDGKR'),
    'OPA2192IDR': (SYS_LIB, 'b611946758d44af680152b979c4a9949', 'OPA2192IDR'),
    'SMA_KE_5': (SYS_LIB, '7f1793f875f5470c9a4a745fe4906f81', 'SMA-KE-5'),
    'HDR_2X20P': (PROJ_LIB, '5ffce60304d857ad', 'PZ254-2-20-W-8.5'),
    'HDR_2X20P_SYS': (SYS_LIB, '952efa9fbe6142a5a453d0227d041eb5', 'PZ254-2-20-W-8.5'),
    # Clock Tree ICs & Connectors
    'ADF4002BRUZ': (SYS_LIB, 'b1ff0e0bb8d540ba9fd725ab0fd4ae49', 'ADF4002BRUZ'),
    'DOIFITQKY_100M': (PROJ_LIB, '5e15ff4f82abc8b8', 'DOIFITQKY-100M'),
    'DOIFITQKY_100M_SYS': (SYS_LIB, 'a660101d2db8469f975a27344df9f0ac', 'DOIFITQKY-100M'),
    'TS5A3159ADBVT': (SYS_LIB, 'fc8fcd3ef3914f93a7828c8bea5f95cf', 'TS5A3159ADBVT'),
    '74LVC1G14GW': (SYS_LIB, '107a89e7baa64da9adbcf41a648eac86', '74LVC1G14GW,125'),
    '74LVC1G04GW': (SYS_LIB, 'd8951d388e4c4114a22daef022deec44', '74LVC1G04GW,125'),
    'SN74AHCT1G125DBVR': (SYS_LIB, '5fcea5cc75e24921b04effc60b3314ec', 'SN74AHCT1G125DBVR'),
    'LTC6957HMS_2': (SYS_LIB, 'b0076317ad7647eb9d6675214be7c739', 'LTC6957HMS-2#TRPBF'),
    'LMK1D1208RHDT': (SYS_LIB, '989eaba620ff415887f42b690fe87df2', 'LMK1D1208RHDT'),
    'SN65LVDS2DBVT': (SYS_LIB, '0e3d6b2eba6d4c208ccbfc07f279ed7e', 'SN65LVDS2DBVT'),
    '74LVC163PW': (SYS_LIB, 'cc27d733e7514e13abdb3b6bb5762b05', '74LVC163PW,118'),
    '74LVC1G74DC': (SYS_LIB, 'a523cef9cbaa45b5b3ee97c59eb6ad10', '74LVC1G74DC-Q100125'),
    '74LVC2G34GW': (SYS_LIB, '6231fac5083d4393b676d658a99b00bc', '74LVC2G34GW/C2125'),
    'HL2_BNC_50KE': (SYS_LIB, '5b3c42a5c1d349038298439a8595150e', 'BNC 50Ω'),
    'POT_3296W_103': (SYS_LIB, '9ac1578476e044d8b0bc05b5429bd250', '10kΩ 3296W'),
    'BAV99': (SYS_LIB, '00712229fd974e13a58030b4c1fb72d3', 'BAV99'),
    'ESD5Z5V0C': (SYS_LIB, 'a6b403c885734755a5c61c76442f9153', 'ESD5Z5V0C'),
    'BLM18PG121SN1D': (PROJ_LIB, '5c9eac2b7c16cde9', 'BLM18PG121SN1D'),
    # Passives (0402 / 0603 / 1206 / 1210)
    'R49R9_0402': (SYS_LIB, 'aa54b4d0eda64ae08e9266eb00c9ae65', '49.9Ω'),
    'R100R_0402': (SYS_LIB, '77e7403431e8459b85f5edddfde5f8c3', '100Ω'),
    'R33R_0402': (SYS_LIB, '2629d7694a9f40fb82940d2fa5fa448c', '33Ω'),
    'R22K_0402': (SYS_LIB, 'cd71e5ddd0614cdca82a624da6f721b6', '22kΩ'),
    'R5K1_0402': (SYS_LIB, 'e6b74a8e960840dba5a2a19f389fa1b4', '5.1kΩ'),
    'R10K_0402': (SYS_LIB, '78ae44ae36314b57b1c9905d2d96ae10', '10kΩ'),
    'R100K_0402': (SYS_LIB, 'acc294b6661948399f609b41c77ed19f', '100kΩ'),
    'R0R_0603': (SYS_LIB, 'fc38f436091b49a696be03a7955956ed', '0Ω'),
    'R100R_0603': (SYS_LIB, '5303080f43d74b41ae76fc5142aa97e5', '100Ω'),
    'R510R_0603': (SYS_LIB, '33a3102241ba4ff69c357d325e1097f2', '510Ω'),
    'R1K_0603': (SYS_LIB, '18db11499a04403ba8c98e2f7a687fbc', '1kΩ'),
    'R10K_0603': (SYS_LIB, 'b948db94476e4027ac8953235755ec96', '10kΩ'),
    'C100N_0402': (SYS_LIB, '33dbcd8e8b3241828899bb3c808db9eb', '100nF'),
    'C100P_0402': (SYS_LIB, 'abe78330ed9a4647957409d52219e472', '100pF'),
    'C10N_0402': (SYS_LIB, '995804b63f764d0ba1f5f72f7c24e0a8', '10nF'),
    'C22N_0402': (SYS_LIB, 'bb5f85e286ef4edfa36ffdcb9be2111e', '22nF'),
    'C1U_0603': (SYS_LIB, 'f4744ff7405a46a48e360c2c6fadeca3', '1uF'),
    'C1U_0603_TDK': (SYS_LIB, 'ab32cf906a594b6cadc7e3b357f90704', '1uF'),
    'C1N_0603': (SYS_LIB, 'f7218f4330f6417aa864e05da749dbcb', '1nF'),
    'C100N_0603': (SYS_LIB, '96b39256cc3f4d80bd3b503deb4f3328', '100nF'),
    'C100P_0603': (SYS_LIB, 'c52f6dce9a2242039357ababc1e5f2aa', '100pF'),
    'C10U_0603': (SYS_LIB, '80646d555bcf4558bdde69f7f0e5dc8d', '10uF'),
    'C10U_1206': (SYS_LIB, 'd23d5960bd564663b90f19ed4a7af7c6', '10uF'),
    'C330N_1210': (SYS_LIB, 'a7ba830627c043f68e0d8bea1b8a4812', '330nF'),
    'C2U2_1210': (SYS_LIB, '81791d3196a54e4da2781aaf9158e441', '2.2uF'),
    'C47U_1206': (SYS_LIB, '989e44f450a941939f81ac278a4c28ec', '47uF'),
    # Verified golden clktree SYS_LIB parts (bom_catalog.py & stage1_*.js)
    'PESD5V0S1BB': (SYS_LIB, 'c5d8ad809dda47ae8ce962a813b31610', 'PESD5V0S1BB'),
    'SN74LVC1G14': (SYS_LIB, '15084ec5c9c44128ab09f77ef64f472c', 'SN74LVC1G14'),
    'SN74LVC1G04': (SYS_LIB, '51f5d93783ab4bbdae9a0d33e679904b', 'SN74LVC1G04'),
    'C2U2_FILM': (SYS_LIB, '9159b45c22a2477589d837b2a7fdd87b', '2.2uF(Film)'),
    'C22N_C0G': (SYS_LIB, 'f704d4a76ed84b869c819e2273a5ac1e', '22nF(C0G)'),
    'C10U_X7R': (SYS_LIB, 'd749c35ae9fe4ad6b07f2e2149550db8', '10uF'),
    'C1U_0402': (SYS_LIB, '46bc734af51c4e58948298ce9e4a5e0b', '1uF'),
    'POT_20K': (SYS_LIB, '7a48852dc04f455c8dc83a05b39c0934', '20kΩ'),
    'R0R_0402': (SYS_LIB, 'b4609725881a44fab1d65d4001f053a7', '0Ω(DNP)'),
    'R1K_0402': (SYS_LIB, '65abbad5fa864933b552e0f016ece0db', '1kΩ'),
    'R100R_0402_V2': (SYS_LIB, '372a75f52e5c428bb7d965aa9a4dec67', '100Ω'),
    'R10K_0402_V2': (SYS_LIB, 'c3b9baa5ef2e4070a4c0f9e9cd04fe6e', '10kΩ'),
    '2N7002': (SYS_LIB, 'f8007837564a4f1fa0e6b57b81dccb0d', '2N7002'),
    'LED_G': (SYS_LIB, '52fdefd7f63c4d58a4856ea3989e5a74', 'LED_GREEN'),
    'LED_Y': (SYS_LIB, '024957f8ea0f404f9b1e4594e4e9a116', 'LED_YELLOW'),
}


def js(code: str, timeout: int = 180):
    """Execute async JS snippet inside EasyEDA Pro without proxy."""
    body = json.dumps({'code': code, 'timeout': timeout}, ensure_ascii=False).encode('utf-8')
    req = urllib.request.Request(BRIDGE_URL, data=body, headers={'Content-Type': 'application/json'})
    try:
        with _NO_PROXY_OPENER.open(req, timeout=timeout) as r:
            obj = json.loads(r.read().decode('utf-8'))
    except urllib.error.HTTPError as e:
        txt = e.read().decode('utf-8', 'replace')
        raise RuntimeError(f'HTTP {e.code}: {txt[:800]}')
    if not obj.get('success'):
        raise RuntimeError(f"Bridge error: {json.dumps(obj, ensure_ascii=False)[:1500]}")
    return obj.get('result')


def open_page(page_uuid: str, wait_ms: int = 1200) -> str:
    """Return JS preamble to open schematic page."""
    return f"await eda.dmt_EditorControl.openDocument({json.dumps(page_uuid)});\nawait new Promise(r=>setTimeout(r,{wait_ms}));\n"


def get_pages():
    """Return list of {name, uuid} for Schematic1."""
    return js(f"""
const scs = await eda.dmt_Schematic.getAllSchematicsInfo();
const sc = (scs||[]).find(s => s.uuid === '{SCHEMATIC_UUID}') || (scs||[])[0];
return sc ? (sc.page||[]).map(p => ({{name: p.name, uuid: p.uuid}})) : [];
""")


def dump_page(page_uuid: str):
    """Read-only dump of all components (with pins), flags, wires, rects, texts on a schematic page."""
    base = js(open_page(page_uuid, 900) + r"""
const comps = (await eda.sch_PrimitiveComponent.getAll()) || [];
const reals = [], flags = [];
for (const c of comps) {
  let ct = null; try { ct = c.getState_ComponentType(); } catch(e){}
  if (String(ct) === 'sheet') continue;
  const pid = c.getState_PrimitiveId();
  let des = null; try { des = c.getState_Designator(); } catch(e){}
  const x = c.getState_X(), y = c.getState_Y(), rot = c.getState_Rotation();
  let net = null; try { net = c.getState_Net(); } catch(e){}
  let nm = null; try { nm = c.getState_Name(); } catch(e){}
  let sub = null; try { sub = c.getState_SubPartName(); } catch(e){}
  let bom = null; try { bom = c.getState_AddIntoBom(); } catch(e){}
  let pcb = null; try { pcb = c.getState_AddIntoPcb(); } catch(e){}
  if (des && String(ct) !== 'netflag' && String(ct) !== 'netport') {
    reals.push({pid, des, nm, sub, x, y, rot, ct, bom, pcb});
  } else {
    flags.push({pid, net, x, y, rot, ct, sub});
  }
}
const ws = (await eda.sch_PrimitiveWire.getAll()) || [];
const wires = ws.map(w => ({pid: w.getState_PrimitiveId(), net: w.getState_Net() || '', line: w.getState_Line()}));
const rects = ((await eda.sch_PrimitiveRectangle.getAll()) || []).map(r => r.getState_PrimitiveId());
const texts = ((await eda.sch_PrimitiveText.getAll()) || []).map(t => {
  let content = '';
  try { content = t.getState_Content(); } catch(e) {}
  return {pid: t.getState_PrimitiveId(), x: t.getState_X(), y: t.getState_Y(), text: content};
});
return {reals, flags, wires, rects, texts};
""", timeout=45)
    meta_by_id = {r['pid']: r for r in base['reals']}
    pids = [r['pid'] for r in base['reals']]
    out_reals = []
    for i in range(0, len(pids), 15):
        chunk = pids[i:i + 15]
        pins_map = js(f"""
const ids = {json.dumps(chunk)};
const out = [];
for (const id of ids) {{
  const c = await eda.sch_PrimitiveComponent.get(id);
  let ps = [];
  if (c && c.getAllPins) {{
    try {{ ps = (await c.getAllPins()) || []; }} catch(e) {{}}
  }}
  out.push([id, ps.map(p => [p.getState_PinNumber(), p.getState_PinName(), p.getState_X(), p.getState_Y(), p.getState_Rotation()])]);
}}
return out;
""", timeout=45)
        for pid, pins in pins_map:
            rec = dict(meta_by_id[pid])
            rec['pins'] = pins
            out_reals.append(rec)
    base['reals'] = out_reals
    return base
