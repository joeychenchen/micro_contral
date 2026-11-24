import json, re, sys

# Expected nets from 参考时钟_选型与连接规格_v1.md §6
EXPECTED_NETS = {
    'OCXO_VC':       ['U18.VC', 'R52', 'C52', 'R39'],
    'OCXO_VREF':     ['U18.VREF', 'U22.VINA+', 'R38'],
    'OCXO_RF':       ['U18.FOUT', 'R55', 'C55'],
    '5vosc':         ['L19'],
    'OCXO_5V_FILT':  ['L19', 'C81', 'C82', 'C83', 'U18.VCC'],
    'EXTREF_IN':     ['J_REFIN.5', 'D2', 'R40', 'C40', 'C41'],
    'EXTREF_AC':     ['C40', 'D1.3', 'R41'],
    'ADF_REFIN':     ['R41', 'U20.REFIN'],
    'EXTREF_DET_AC': ['C41', 'R42', 'R43', 'U24.A'],
    'EXTREF_DET':    ['U24.Y'],
    'LF_CP':         ['U20.CP', 'C47', 'R47', 'R48'],
    'LF_Z':          ['R47', 'C48'],
    'LF_OUT':        ['R48', 'C49', 'U23.NO'],
    'DAC_VREF':      ['U22.VOUTA', 'U22.VINA-', 'U21.VREF', 'C51'],
    'DAC_VOUT':      ['U21.VOUT', 'U21.VFB', 'R50'],
    'DAC_VC':        ['R50', 'C50', 'U23.NC'],
    'VC_SW':         ['U23.COM', 'U22.VINB+'],
    'VC_BUF':        ['U22.VOUTB', 'U22.VINB-', 'R52', 'R53'],
    'VC_MON':        ['R53', 'R54', 'C54'],
    'REF_SEL':       ['U23.IN', 'R51', 'Q11'],
    'REF_LOCK':      ['U20.MUXOUT', 'Q10'],
    'SPI_REF_SCK':   ['U20.CLK', 'U21.SCLK'],
    'SPI_REF_MOSI':  ['U20.DATA', 'U21.DIN'],
    'ADF_LE':        ['U20.LE', 'R49'],
    'ADF_CE':        ['U20.CE', 'R44'],
    'DAC_SYNC_N':    ['U21.SYNC#', 'R56'],
    'CLK_LVDS_P':    ['U25.OUT1+', 'U26.IN0_P', 'R57'],
    'CLK_LVDS_N':    ['U25.OUT1–', 'U26.IN0_N', 'R57'],
    'CLK100_DDSA_P': ['U26.OUT0_P'],
    'CLK100_DDSA_N': ['U26.OUT0_N'],
    'CLK100_DDSB_P': ['U26.OUT1_P'],
    'CLK100_DDSB_N': ['U26.OUT1_N'],
    'CLK100_LMXA_P': ['U26.OUT2_P'],
    'CLK100_LMXA_N': ['U26.OUT2_N'],
    'CLK100_LMXB_P': ['U26.OUT3_P'],
    'CLK100_LMXB_N': ['U26.OUT3_N'],
    'CLK_FB_P':      ['U26.OUT4_P', 'R45', 'C45'],
    'CLK_FB_N':      ['U26.OUT4_N', 'R45', 'C46'],
    'ADF_RFINA':     ['C45', 'U20.RFINA'],
    'ADF_RFINB':     ['C46', 'U20.RFINB'],
    'CLK100_DIV_P':  ['U26.OUT5_P', 'R58', 'U27.A'],
    'CLK100_DIV_N':  ['U26.OUT5_N', 'R58', 'U27.B'],
    'CLK100_CMOS':   ['U27.R', 'U28.CP'],
    'CLK20':         ['U28.Q2', 'U33.A', 'U29.CP'],
    'U28_LOAD_N':    ['U33.Y', 'U28.PE#'],
    'CLK10_N':       ['U29.D', 'U29.Q#'],
    'CLK10':         ['U29.Q', 'U30.1A', 'U30.2A'],
    'REFOUT_DRV':    ['U30.1Y', 'U30.2Y', 'R60'],
    'REFOUT_BNC':    ['R60', 'C60', 'J_REFOUT.5'],
}

def parse_protel_netlist(nl):
    idx = nl.rfind(']')
    nets_section = nl[idx+1:] if idx >= 0 else nl
    net_blocks = re.findall(r'\(\s*([^\r\n]+)\s*(.*?)\s*\)', nets_section, re.S)
    nets = {}
    for net_name, body in net_blocks:
        pins = [l.strip() for l in body.splitlines() if l.strip()]
        nets[net_name.strip()] = pins
    return nets

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python netlist_verifier.py <json_with_netlist>")
        sys.exit(0)
    with open(sys.argv[1], encoding='utf-8') as f:
        d = json.load(f)
    nl = d.get('result', d).get('netlist', '')
    nets = parse_protel_netlist(nl)
    print(f"Total nets in exported netlist: {len(nets)}")
    ok = 0
    issues = []
    for net, reqs in EXPECTED_NETS.items():
        actual = nets.get(net)
        if not actual:
            issues.append(f"MISSING NET: {net} (expected {reqs})")
            continue
        actual_str = " | ".join(actual)
        missing = []
        for req in reqs:
            if '.' in req:
                des, pname = req.split('.', 1)
                # match des-pinnum ...-pname
                pat = rf'\b{re.escape(des)}-(?:{re.escape(pname)}\b|\S+\s+\S*-{re.escape(pname)}\b)'
                if not re.search(pat, actual_str):
                    # fallback check both des- and -pname in same entry
                    found = any(p.startswith(des + '-') and (p.endswith('-' + pname + ' Passive') or p.endswith('-' + pname + ' Input') or p.endswith('-' + pname + ' Output') or f'-{pname} ' in p or p.startswith(f'{des}-{pname} ')) for p in actual)
                    if not found:
                        missing.append(req)
            else:
                if not any(p.startswith(req + '-') for p in actual):
                    missing.append(req)
        if missing:
            issues.append(f"NET {net}: missing {missing} | actual={actual}")
        else:
            ok += 1
    # Check for unexpected auto-named nets ($...) with >1 pin or unexpected big nets
    auto_multi = {k: v for k, v in nets.items() if k.startswith('$') and len(v) > 1}
    print(f"Verified {ok}/{len(EXPECTED_NETS)} expected signal nets OK.")
    if issues:
        print("\n=== ISSUES ===")
        for it in issues:
            print("  !", it)
    if auto_multi:
        print("\n=== AUTO-NAMED MULTI-PIN NETS ===")
        for k, v in auto_multi.items():
            print(f"  {k}: {v}")
    print("\n=== POWER/GROUND NETS ===")
    for k in sorted(nets.keys()):
        if any(p in k for p in ('GND', '3V3', '5VA', '5vosc', 'VCC', '6V8')):
            print(f"  {k:16s} ({len(nets[k]):3d} pins)")
