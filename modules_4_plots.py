#!/usr/bin/env python3

import ROOT
import click

_dummy_histos = []

@click.command()
@click.argument("root_file", type=click.Path(exists=True))
@click.option("-k", "--key-substring", default="D_B(0)_O(0)_H(0)_PixelAlive")
@click.option("-m", "--module-name", default="MODULE-NAME")
@click.option("-c", "--color-palette", is_flag=True, default=False)
@click.option("--logz", is_flag=True, default=False)
@click.option("--colz", is_flag=True, default=False)
@click.option("--inverse", is_flag=True, default=False, help="Flip all chips vertically (mirror over X axis)")
@click.option(
    "-md", "--methods",
    type=click.Choice(["Fwd", "Cross", "Xray"], case_sensitive=True),
    multiple=True,
    help="Methods to compare: Fwd, Cross, Xray"
)

def plot_module(root_file, key_substring, module_name, methods, color_palette, logz, colz, inverse):
    ROOT.gStyle.SetOptStat(0)
    
    if color_palette:
        ROOT.gStyle.SetPalette(ROOT.kDarkBodyRadiator)
    else:
        ROOT.gStyle.SetPalette(ROOT.kGreyScale)    

    f = ROOT.TFile.Open(root_file)
    chip_order = [12, 13, 15, 14]
    axes = {12: (True, False), 13: (False, False), 15: (True, True), 14: (False, True)}
    if inverse:
        axes = {15: (True, False), 14: (False, False), 12: (True, True), 13: (False, True)}
    chip_histos = {}

    for cid in chip_order:
        obj = find_canvas_or_th2(f, key_substring, cid)
        if not obj:
            continue
        th2_list = find_th2_objects(obj)
        if not th2_list:
            continue
        hists = []
        for i, h in enumerate(th2_list):
            hist = h.Clone(f"chip_{cid}_{i}")
            hist.SetDirectory(0)
            if cid in [14, 15]:
                hist = rotate_180(hist)
                
            if inverse:
                hist = flip_x(hist)  
            hist.SetStats(0)
            hists.append(hist)
        chip_histos[cid] = hists



    # Tamaños
    W, H_MAIN, H_TIT, H_LEG = 1150, 760, 40, 60
    c = ROOT.TCanvas("main_canvas", module_name, W, H_MAIN + H_TIT + H_LEG)

    # Pads
    pTitle = ROOT.TPad("pTitle", "", 0, (H_MAIN + H_LEG)/(H_MAIN + H_TIT + H_LEG), 1, 1) 
    pMain  = ROOT.TPad("pMain",  "", 0, H_LEG/(H_MAIN + H_TIT + H_LEG), 1, (H_MAIN + H_LEG)/(H_MAIN + H_TIT + H_LEG))
    pLeg   = ROOT.TPad("pLeg",   "", 0, 0, 1, H_LEG/(H_MAIN + H_TIT + H_LEG))

    for p in (pTitle, pMain, pLeg):
        p.SetFillStyle(0)
        p.SetBorderSize(0)
        p.Draw()
    
    # Título
    pTitle.cd()
    title = ROOT.TPaveText(0.1, 0, 0.9, 1, "brNDC")
    title.SetFillColor(0)
    title.SetBorderSize(0)
    title.SetTextFont(62)
    title.SetTextSize(0.8)
    title.AddText(f"Module: {module_name}")
    title.Draw()


    canvas_order = [12, 13, 15, 14]
    if inverse:
        canvas_order = [15, 14, 12, 13]
        
        
    # Histos
    pMain.cd()
    pMain.Divide(2, 2, 0.0001, 0.0001)
    for i, cid in enumerate(canvas_order):
        if cid in chip_histos:
            pad = pMain.cd(i + 1)
            if logz:
                pad.SetLogz()
            for j, h in enumerate(chip_histos[cid]):
                h.SetMinimum(5e-7)
                h.SetMaximum(3e-3)
                if j == 0:
                    configure_axes(h, pad=pad, left=axes[cid][0], bottom=axes[cid][1])
                opt = "COL" if colz else "BOXF"    
                if j > 0:
                    opt += " SAME"
                h.Draw(opt)

    # Leyenda
    pLeg.cd()
    
    if key_substring == "D_B(0)_O(0)_H(0)_PixelAlive":
        pass
    else:
    
        leg = ROOT.TLegend(0.1, 0.05, 0.9, 1)

        method_set = set(m.lower() for m in methods)
        leg.SetFillColor(0)
        leg.SetBorderSize(1)
        leg.SetTextAlign(22)    
        leg.SetTextSize(0.45)

        if method_set == {"fwd", "cross", "xray"}:
            leg.SetNColumns(4)
            legend_items = [
                (ROOT.kGreen+2,  "Only X-ray"),
                (ROOT.kBlue,     "Only Crosstalk"),
                (ROOT.kRed,      "Only Fwd"),
                (ROOT.kOrange+7, "Crosstalk & X-ray"),
                (ROOT.kTeal+3,   "Fwd & X-ray"),        
                (ROOT.kMagenta+1,"Fwd & Crosstalk"),
                (ROOT.kBlack,    "All 3 methods"),
            ]
        elif method_set == {"fwd", "cross"}:
            leg.SetNColumns(2)    
            legend_items = [
                (ROOT.kRed,        "Only Fwd"),    
                (ROOT.kBlue,       "Only Crosstalk"),
                (ROOT.kMagenta+1,  "Fwd & Crosstalk"),
            ]
        elif method_set == {"cross", "xray"}:
            leg.SetNColumns(2)
            legend_items = [
                (ROOT.kGreen+2,    "Only X-ray"),
                (ROOT.kBlue,       "Only Crosstalk"),
                (ROOT.kOrange+7,   "Crosstalk & X-ray"),    
            ]
        elif method_set == {"fwd", "xray"}:
            leg.SetNColumns(2)
            legend_items = [
                (ROOT.kGreen+2,    "Only X-ray"),
                (ROOT.kRed,        "Only Fwd"),    
                (ROOT.kTeal+3,     "Fwd & X-ray"),    
            ]   
        
        else:
            leg.SetNColumns(3)
            problematic_label = "Hits<200" if module_name == "I-102" and method_set == {"Xray"} else "Problematic"
            problematic_color = ROOT.kBlue if module_name == "I-102" and method_set == {"Xray"} else ROOT.kOrange+7
            
            legend_items = []

            if module_name == "I-102" or method_set == {"cross"}:
                legend_items.append((ROOT.kGreen+2, "Masked"))

            legend_items.extend([
                (ROOT.kRed,     "Missing"),
                (problematic_color, problematic_label),
            ])
  
    
        for color, label in legend_items:
            dummy = ROOT.TH1F("", "", 1, 0, 1)
            dummy.SetFillColor(color)
            dummy.SetLineColor(color)    
            dummy.SetDirectory(0)
            _dummy_histos.append(dummy)
            leg.AddEntry(dummy, label, "f")
        leg.Draw()

    c.Update()
    output_name = f"{key_substring}_{module_name}.png"
    if inverse: 
        output_name = f"{key_substring}_{module_name}_topv.png"
    c.SaveAs(output_name)
    print(f"Imagen guardada como: {output_name}")
    input("Presiona Enter para cerrar...")

# ──────────────── FUNCIONES AUXILIARES ────────────────
def configure_axes(h, pad=None, left=False, bottom=False):
    h.GetXaxis().SetLabelSize(0 if not bottom else h.GetXaxis().GetLabelSize())
    h.GetYaxis().SetLabelSize(0 if not left else h.GetYaxis().GetLabelSize())
    h.GetXaxis().SetTitleSize(0 if not bottom else 20)
    h.GetYaxis().SetTitleSize(0 if not left else 20)
    
    h.GetXaxis().SetTitle("Columns" if (not left and bottom) else "")
    h.GetYaxis().SetTitle("Rows" if (left and not bottom) else "")    
    
    if pad:
        if not left and not bottom:
            pad.SetLeftMargin(0)
            pad.SetBottomMargin(0)
            pad.SetRightMargin(0.12)
            pad.SetTopMargin(0.12)
    
        if not left and bottom:
            pad.SetLeftMargin(0)
            pad.SetTopMargin(0)
            pad.SetRightMargin(0.12)
            pad.SetBottomMargin(0.12)
        
        if left and bottom:
            pad.SetRightMargin(0)
            pad.SetTopMargin(0)
            pad.SetLeftMargin(0.12)
            pad.SetBottomMargin(0.12)
                    
        if left and not bottom:
            pad.SetBottomMargin(0)
            pad.SetRightMargin(0)
            pad.SetLeftMargin(0.12)
            pad.SetTopMargin(0.12)
           
   
      
def rotate_180(h):
    nbinsX, nbinsY = h.GetNbinsX(), h.GetNbinsY()
    rh = h.Clone(h.GetName() + "_rotated")
    for ix in range(1, nbinsX + 1):
        for iy in range(1, nbinsY + 1):
            rh.SetBinContent(nbinsX - ix + 1, nbinsY - iy + 1, h.GetBinContent(ix, iy))
    rh.SetDirectory(0)
    return rh

def find_th2_objects(obj):
    th2_list = []
    if obj.InheritsFrom("TH2"):
        th2_list.append(obj)
    elif obj.InheritsFrom("TPad") or obj.InheritsFrom("TCanvas"):
        for prim in obj.GetListOfPrimitives():
            th2_list.extend(find_th2_objects(prim))
    return th2_list

def find_canvas_or_th2(tdir, key_substr, chip_id):
    for key in tdir.GetListOfKeys():
        key_name = key.GetName()
        cls = key.GetClassName()
        if key_substr in key_name and f"Chip({chip_id})" in key_name:
            return key.ReadObj()
        if cls in ("TDirectory", "TDirectoryFile"):
            subdir = key.ReadObj()
            found = find_canvas_or_th2(subdir, key_substr, chip_id)
            if found: return found
    return None



def flip_x(h):
    """Flip only in the vertical direction (eje X del canvas → eje Y del histograma)"""
    nbinsX = h.GetNbinsX()
    nbinsY = h.GetNbinsY()
    rh = h.Clone(h.GetName() + "_flipx")
    for ix in range(1, nbinsX + 1):
        for iy in range(1, nbinsY + 1):
            new_y = nbinsY - iy + 1
            rh.SetBinContent(ix, new_y, h.GetBinContent(ix, iy))
    return rh
    
    
# ───────────────────────────────
if __name__ == '__main__':
    plot_module()


