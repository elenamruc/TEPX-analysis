
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Overlap of bad-bump maps produced by the three methods

• Fwd–Reverse   :  …/FwdReverse_analysis/BadBumps_fwdrev_XX.txt
• Cross-Talk    :  …/Crosstalk_method_analysis/BadBumps_CrossTalk_XX.txt
• X-ray         :  …/Xray_method_analysis/BadBumps_Xray_XX.txt   (❗ keep ONLY
                   the "Missing" section, ignore "Problematic")

Outputs a colour-coded PNG and stores the canvases in overlap_allMods.root
for chips 12, 13, 14, 15.
"""

import ROOT, os, click, re, itertools as it
@click.command()
@click.option("-m", "--module-name", default="MODULE-NAME")
@click.option(
    "-md", "--methods",
    type=click.Choice(["Fwd", "Cross", "Xray"], case_sensitive=True),
    multiple=True,
    help="Methods to compare: Fwd, Cross, Xray"
)

def main(module_name, methods):
    OUT_DIR = "BadBumps_overlap"
    os.makedirs(OUT_DIR, exist_ok=True)
    root_out = ROOT.TFile(os.path.join(OUT_DIR, f"{methods}_Mods.root"), "RECREATE")

    for chip in (15,14,13,12):
        make_overlap_map(chip, module_name, root_out, OUT_DIR, methods)

    root_out.Close()
    print("All overlap maps stored in", OUT_DIR)       
        
        
# ────────── look & feel identical to your other maps ─────────────────────────
ROOT.gStyle.SetPalette(ROOT.kRainBow)
ROOT.gStyle.SetNumberContours(255)
ROOT.gStyle.SetOptStat(0)
for ax in "XY":
    ROOT.gStyle.SetTitleFont (43, ax)
    ROOT.gStyle.SetTitleSize (34, ax)
    ROOT.gStyle.SetLabelFont(43, ax)
    ROOT.gStyle.SetLabelSize(24, ax)



# ────────── tiny helper to read one of your .txt files ───────────────────────
_rx = re.compile(r"\s*(\d+)\s*,\s*(\d+)")
def read_txt(path, keep_problematic=True):
    missing, problematic = set(), set()
    if not os.path.isfile(path):
        return missing, problematic
    current = None
    with open(path) as f:
        for line in f:
            l = line.strip().lower()
            if l.startswith("missing"):
                current = missing; continue
            if l.startswith("problem"):
                current = problematic; continue
            m = _rx.match(line)
            if m and current is not None:
                current.add(tuple(map(int, m.groups())))
    if not keep_problematic:
        problematic.clear()
    return missing, problematic     # two disjoint sets


def make_overlap_map(chip, module, root_out, OUT_DIR, methods, nX=432, nY=336):
    # Leer los datos de los métodos indicados
    F = C = X = set()
    paths = {}
    if "Fwd" in methods:
        paths["Fwd"] = f"{module}_forward_bias_method/FwdReverse_analysis/BadBumps_fwdrev_{chip}.txt"
    if "Cross" in methods:
        paths["Cross"] = f"{module}_crosstalk-method/Crosstalk_method_analysis/BadBumps_CrossTalk_{chip}.txt"
    if "Xray" in methods:
        paths["Xray"] = f"{module}_Xray_method/Xray_method_analysis/BadBumps_Xray_{chip}.txt"

    # Si falta alguno de los archivos requeridos, salir
    for m, path in paths.items():
        if not os.path.isfile(path):
            print(f"[INFO] Chip {chip}: file for {m} method not found → {path}")
            return

    if "Fwd" in methods:
        Fm, Fp = read_txt(f"{module}_forward_bias_method/FwdReverse_analysis/BadBumps_fwdrev_{chip}.txt")
        F = Fm | Fp

    if "Cross" in methods:
        Cm, Cp = read_txt(f"{module}_crosstalk-method/Crosstalk_method_analysis/BadBumps_CrossTalk_{chip}.txt")
        C = Cm | Cp

    if "Xray" in methods:
        Xm, _ = read_txt(f"{module}_Xray_method/Xray_method_analysis/BadBumps_Xray_{chip}.txt", keep_problematic=False)
        X = Xm

    # Determinar clases y colores según los métodos disponibles
    classes, COL = {}, {}

    if set(methods) == {"Fwd", "Cross", "Xray"}:
        classes = {
            "All 3":  F & C & X,
            "Fwd & Cross":   (F & C) - X,
            "Fwd & X-ray":   (F & X) - C,
            "Cross & X-ray":   (C & X) - F,
            "Only Fwd": F - (C | X),
            "Only Cross": C - (F | X),
            "Only X-ray": X - (F | C),
        }
        COL = {
            "All 3":  ROOT.kBlack,
            "Fwd & Cross":   ROOT.kMagenta + 1,
            "Fwd & X-ray":   ROOT.kTeal + 3,
            "Cross & X-ray":   ROOT.kOrange + 7,
            "Only Fwd": ROOT.kRed,
            "Only Cross": ROOT.kBlue,
            "Only X-ray": ROOT.kGreen + 2,
        }

    elif set(methods) == {"Fwd", "Cross"}:
        classes = {
            "Fwd & Cross":   F & C,
            "Only Fwd": F - C,
            "Only Cross": C - F,
        }
        COL = {
            "Fwd & Cross":   ROOT.kMagenta + 1,
            "Only Fwd": ROOT.kRed,
            "Only Cross": ROOT.kBlue,
        }

    elif set(methods) == {"Fwd", "Xray"}:
        classes = {
            "Fwd & X-ray":   F & X,
            "Only Fwd": F - X,
            "Only X-ray": X - F,
        }
        COL = {
            "Fwd & X-ray":   ROOT.kTeal + 3,
            "Only Fwd": ROOT.kRed,
            "Only X-ray": ROOT.kGreen + 2,
        }

    elif set(methods) == {"Cross", "Xray"}:
        classes = {
            "Cross & X-ray":   C & X,
            "Only Cross": C - X,
            "Only X-ray": X - C,
        }
        COL = {
            "Cross & X-ray":   ROOT.kOrange + 7,
            "Only Cross": ROOT.kBlue,
            "Only X-ray": ROOT.kGreen + 2,
        }

    else:
        print(f"[⚠] Invalid or insufficient method combination: {methods}")
        return
        

    # Crear mapas de cada clase
    hmaps = {k: ROOT.TH2I(f"h_{k}_{chip}", "", nX, 0, nX, nY, 0, nY) for k in classes}
    for k, pset in classes.items():
        h = hmaps[k]
        h.SetFillColor(COL[k])
        h.SetStats(0)
        h.GetXaxis().SetTitle("Columns")
        h.GetYaxis().SetTitle("Rows")
        for (c, r) in pset:
            h.SetBinContent(c + 1, r + 1, 1)

    # Crear canvas
    W, H_H, H_L = 1150, 800, 60
    frac = H_L / float(H_H + H_L)
    c = ROOT.TCanvas(f"c_overlap_{chip}", "", W, H_H + H_L)
    pH = ROOT.TPad("pH", "", 0, frac, 1, 1)
    pL = ROOT.TPad("pL", "", 0, 0, 1, frac)
    for p in (pH, pL):
        p.SetFillStyle(0)
        p.SetBorderSize(0)
        p.Draw()
    pH.SetTopMargin(.10)
    pH.SetLeftMargin(.10)
    pH.SetRightMargin(.10)
    pH.SetBottomMargin(.12)
    pH.cd()

    # Dibujar primer mapa válido
    order = list(classes.keys())
    first_drawn = next((k for k in order if hmaps[k].GetEntries() > 0), None)

    if first_drawn is None:
        dummy = ROOT.TH2I("dummy", "", nX, 0, nX, nY, 0, nY)
        dummy.SetStats(0)
        dummy.GetXaxis().SetTitle("Columns")
        dummy.GetYaxis().SetTitle("Rows")
        dummy.Draw()
    else:
        hmaps[first_drawn].Draw("BOXF")
        for k in order:
            if k != first_drawn and hmaps[k].GetEntries() > 0:
                hmaps[k].Draw("BOXF SAME")

    # Leyenda
    pL.cd()
    leg = ROOT.TLegend(0.10, 0.05, 0.90, 0.95)
    leg.SetNColumns(min(4, len(classes)))
    leg.SetBorderSize(1)
    leg.SetFillColor(0)
    leg.SetTextSize(0.45)
    for k in order:
        leg.AddEntry(hmaps[k], f"{k.replace('&', ' & ')} ({len(classes[k])})", "f")
    leg.Draw()
    c.Update()

    # Guardar PNG
    png = os.path.join(OUT_DIR, f"Compare_{methods}_Chip({chip}).png")
    c.SaveAs(png)

    # Guardar en ROOT
    chip_dir_path = f"Detector/Board_0/OpticalGroup_0/Hybrid_0/Chip_{chip}"
    dirs = chip_dir_path.split("/")
    current_dir = root_out
    for d in dirs:
        current_dir = current_dir.mkdir(d) if not current_dir.GetDirectory(d) else current_dir.GetDirectory(d)
    current_dir.cd()
    c.Write(f"Compare_{methods}_Chip({chip})")

    print(f"✓ {png}")

if __name__=="__main__":
    main()
