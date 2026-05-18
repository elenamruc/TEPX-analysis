
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Fwd-Reverse SCurve analysis  (estética unificada)

Uso:
  python fwd_reverse.py  fwd.root  rev.root  pixelalive.root  [out_dir]

• 1-D  ΔThreshold  (líneas ±40 / ±75 Vcal)
• 1-D  ΔNoise      (líneas ±15 / ±25 Vcal)
• 2-D  mapa ΔThr-ΔNoise
• SummaryMap  (Missing = rojo, Problematic = azul, Masked = verde)
• .txt con coordenadas Missing / Problematic
"""
import ROOT, os, sys
from array import array
from ROOT import TLine

# ─────────────── estilo ROOT global ───────────────
ROOT.gStyle.SetPalette(ROOT.kRainBow)
ROOT.gStyle.SetNumberContours(255)
ROOT.gStyle.SetOptStat(1)

# ─────────────── posiciones de stats (tu función) ───────────────
def format_stats_box(prim, name):
    stats = prim.GetListOfFunctions().FindObject("stats")
    if stats:
        if name == "Noise":
            stats.SetX1NDC(0.68)
            stats.SetY1NDC(0.73)
            stats.SetX2NDC(0.88)
            stats.SetY2NDC(0.88)
        elif name == "Plot_2D":
            stats.SetX1NDC(0.15)
            stats.SetY1NDC(0.71)
            stats.SetX2NDC(0.35)
            stats.SetY2NDC(0.88)        
        elif name == "Threshold":
            stats.SetX1NDC(0.15)
            stats.SetY1NDC(0.71)
            stats.SetX2NDC(0.35)
            stats.SetY2NDC(0.88)
        else:
            stats.SetX1NDC(0.15)
            stats.SetY1NDC(0.73)
            stats.SetX2NDC(0.35)
            stats.SetY2NDC(0.88)
    else:
        print("No stats box found for this histogram.")

def pad_margins(obj):
    for f in (obj.SetTopMargin, obj.SetBottomMargin,
              obj.SetLeftMargin, obj.SetRightMargin):
        f(0.10)

# ─────────────── util búsqueda recursiva ──────────
def find_histogram(tdir, target):
    for key in tdir.GetListOfKeys():
        obj = key.ReadObj()
        if obj.InheritsFrom(ROOT.TH1.Class()) and target in obj.GetName():
            return obj
        if obj.InheritsFrom(ROOT.TCanvas.Class()) and target in obj.GetName():
            for p in obj.GetListOfPrimitives():
                if p.InheritsFrom(ROOT.TH1.Class()): return p
        if obj.InheritsFrom(ROOT.TDirectory.Class()):
            out = find_histogram(obj, target)
            if out: return out
    return None

# ─────────────── umbrales de la tarea ─────────────
THR_MISS, THR_PROB =  40, 75   # Vcal
NOI_MISS, NOI_PROB =  15, 25   # Vcal

def classify_pixel(dthr, dnoi, masked):
    if masked:          return 0
    if abs(dthr) <= THR_MISS and abs(dnoi) <= NOI_MISS:  return 1   # Missing
    if abs(dthr) <= THR_PROB and abs(dnoi) <= NOI_PROB:  return 2   # Problematic
    return 0

# ─────────────── figuras 1-D shift ────────────────
def plot_shift_1d(h_fwd, h_rev, tag, limit_miss, limit_prob, out_dir, chip, root_out, chip_dir):
    rng = (-3000, 3000) if tag=="Threshold" else (-500, 500)
    h1 = ROOT.TH1F(f"{tag} Shift", f";{tag} Shift (#DeltaVcal);Number of Pixels",
                   3000, *rng)
    nx, ny = h_fwd.GetNbinsX(), h_fwd.GetNbinsY()
    for ix in range(1,nx+1):
        for iy in range(1,ny+1):
            h1.Fill(h_fwd.GetBinContent(ix,iy) - h_rev.GetBinContent(ix,iy))

    c = ROOT.TCanvas(f"c_{tag}_{chip}","",1150,800); pad_margins(c)
    c.SetLeftMargin(0.12)
    c.SetLogy(); h1.SetLineWidth(2); h1.Draw("HIST")
    
    
    h1.GetXaxis().SetTitleSize(34)
    h1.GetXaxis().SetTitleFont(43)
    h1.GetYaxis().SetTitleSize(34)
    h1.GetYaxis().SetTitleFont(43)
    h1.GetXaxis().SetLabelSize(0.04)
    h1.GetYaxis().SetLabelSize(0.04)

    h1.Draw()    

    # Líneas rojas
    ymax = h1.GetMaximum() * 1.05
    l1_miss = TLine(-limit_miss, 0, -limit_miss, ymax)
    l1_miss.SetLineColor(ROOT.kRed); l1_miss.SetLineWidth(2); l1_miss.Draw()
    
    l2_miss = TLine(limit_miss, 0, limit_miss, ymax)
    l2_miss.SetLineColor(ROOT.kRed); l2_miss.SetLineWidth(2); l2_miss.Draw()
    
    l1_prob = TLine(-limit_prob, 0, -limit_prob, ymax)
    l1_prob.SetLineColor(ROOT.kOrange+7); l1_prob.SetLineWidth(2); l1_prob.Draw()
    
    l2_prob = TLine(limit_prob, 0, limit_prob, ymax)
    l2_prob.SetLineColor(ROOT.kOrange+7); l2_prob.SetLineWidth(2); l2_prob.Draw()

    c.Update()
    
    format_stats_box(h1, f"{tag}")
    
     
    png = os.path.join(out_dir, f"{tag}_Shift_Chip({chip}).png")
    c.SaveAs(png); print("Save", png)
    chip_dir.cd()
    chip_dir.WriteTObject(c, f"{tag}_Shift_Chip({chip})")
    
    

# ─────────────── figura 2-D ΔThr-ΔNoise ───────────
def plot_shift_2d(dthr, dnoi, out_dir, chip, root_out, chip_dir):
    h2 = ROOT.TH2F(f"Threshold vs Noise Shift","2D Vcal Differences;Threshold Shift (#DeltaVcal);Noise Shift (#DeltaVcal)",
                   3000,-3800,3800,3000,-200,200)
    for x,y in zip(dthr,dnoi): h2.Fill(x,y)

    c = ROOT.TCanvas(f"c_2d_{chip}","",1150,800); pad_margins(c)
    
    c.Clear(); c.SetLogy(False)
    c.cd() 
    c.SetLeftMargin(0.1)
    c.SetRightMargin(0.17)
    
    h2.SetTitle("")
    
    
    # Configure the size and font of the axis titles
    h2.SetZTitle("Number of Pixels")
    h2.GetXaxis().SetTitleSize(34)
    h2.GetXaxis().SetTitleFont(43)
    h2.GetYaxis().SetTitleSize(34)
    h2.GetYaxis().SetTitleFont(43)
    h2.GetZaxis().SetTitleSize(34)  
    h2.GetZaxis().SetTitleFont(43) 
    h2.GetZaxis().SetTitleOffset(1.8)
    h2.GetXaxis().SetLabelSize(0.04)  
    h2.GetYaxis().SetLabelSize(0.04) 
    h2.GetZaxis().SetLabelSize(0.04)    
    
    h2.Draw("COLZ")
    c.Update(); format_stats_box(h2, "Plot_2D")
    # Ajusta la posición de la barra de colores
    pal = h2.GetListOfFunctions().FindObject("palette")
    if pal:
        pal.SetX1NDC(0.83); pal.SetX2NDC(0.87)
        pal.SetY1NDC(c.GetBottomMargin())
        pal.SetY2NDC(1 - c.GetTopMargin()) 
        
        
    red_lim_x = (-THR_MISS, THR_MISS)
    red_lim_y = (-NOI_MISS, NOI_MISS)
    orange_lim_x = (-THR_PROB, THR_PROB)
    orange_lim_y = (-NOI_PROB, NOI_PROB)

    # Rectángulo rojo (Missing)
    box_red = ROOT.TBox(red_lim_x[0], red_lim_y[0], red_lim_x[1], red_lim_y[1])
    box_red.SetLineColor(ROOT.kRed); box_red.SetLineWidth(2); box_red.SetFillStyle(0)
    box_red.Draw()

    # Rectángulo naranja (Problematic)
    box_orange = ROOT.TBox(orange_lim_x[0], orange_lim_y[0], orange_lim_x[1], orange_lim_y[1])
    box_orange.SetLineColor(ROOT.kOrange+7); box_orange.SetLineWidth(2); box_orange.SetLineStyle(0); box_orange.SetFillStyle(0)
    box_orange.Draw()

    png = os.path.join(out_dir, f"Thr_vs_Noise_Shift_Chip({chip}).png")
    c.SaveAs(png); print("Save", png)
    chip_dir.cd()
    chip_dir.WriteTObject(c, f"Thr_vs_Noise_Shift_Chip({chip})")

# ─────────────── mapa sensor final ────────────────
def draw_summary(h_mask_in, dThr, dNoi, out_dir, chip, root_out, chip_dir):
    nx, ny = h_mask_in.GetNbinsX(), h_mask_in.GetNbinsY()
    h_miss = ROOT.TH2I("h_miss","",nx,0,nx,ny,0,ny)
    h_prob = ROOT.TH2I("h_prob","",nx,0,nx,ny,0,ny)
    h_mask = ROOT.TH2I("h_mask","",nx,0,nx,ny,0,ny)   # solo para dibujar

    coords = {"miss":[], "prob":[]}
    for ix in range(1,nx+1):
        for iy in range(1,ny+1):
            masked = (h_mask_in.GetBinContent(ix,iy)!=0)
            cat = classify_pixel(dThr[(ix-1)*ny+iy-1], dNoi[(ix-1)*ny+iy-1], masked)
            if masked:      h_mask.SetBinContent(ix,iy,1)
            elif cat==1:    h_miss.SetBinContent(ix,iy,1); coords["miss"].append((ix-1,iy-1))
            elif cat==2:    h_prob.SetBinContent(ix,iy,1); coords["prob"].append((ix-1,iy-1))

    for h,c in ((h_miss,ROOT.kRed), (h_prob,ROOT.kOrange+7), (h_mask,ROOT.kGreen+2)):
        h.SetFillColor(c); h.SetStats(0)
        h.GetXaxis().SetTitle("Columns"); h.GetYaxis().SetTitle("Rows")
        #h.SetTitle(f"Missing Bumps – CrossTalk (I-102 Mod {chip})")

        h.GetXaxis().SetTitleSize(34)
        h.GetXaxis().SetTitleFont(43)
        h.GetYaxis().SetTitleSize(34)
        h.GetYaxis().SetTitleFont(43)
        h.GetXaxis().SetLabelSize(0.04)
        h.GetYaxis().SetLabelSize(0.04)

        h.Draw()  

    # Canvas con banda inferior
    W,H_H,H_L = 1150,800,40; frac = H_L/float(H_H+H_L)
    c  = ROOT.TCanvas(f"c_sum_{chip}","",W,H_H+H_L)
    pH = ROOT.TPad("pH","",0,frac,1,1); pL = ROOT.TPad("pL","",0,0,1,frac)
    for p in (pH,pL): p.SetFillStyle(0); p.SetBorderSize(0); p.Draw()
    pad_margins(pH); pH.cd()
    h_mask.Draw("BOXF"); h_miss.Draw("BOXF SAME"); h_prob.Draw("BOXF SAME")
    pL.cd()
    leg = ROOT.TLegend(0.10,0.05,0.90,0.95)
    leg.SetNColumns(3); leg.SetBorderSize(1); leg.SetFillColor(0); leg.SetTextAlign(22); leg.SetTextSize(0.75)
    leg.AddEntry(h_miss,f"Missing ({len(coords['miss'])})","f")
    leg.AddEntry(h_prob,f"Problematic ({len(coords['prob'])})","f")
    leg.AddEntry(h_mask,f"Masked ({int(h_mask.GetEntries())})","f")
    leg.Draw(); c.Update()
    
    for m in (c.SetTopMargin, c.SetBottomMargin, c.SetRightMargin):
        m(0.10)
    c.SetLeftMargin(0.12)
    c.Update()


    png = os.path.join(out_dir, f"Fwrd_reverse_badbump_Chip({chip}).png")
    canvas.SaveAs(png)
    chip_dir.cd()
    chip_dir.WriteTObject(canvas, f"Fwrd_reverse_badbump_Chip({chip})")

    txt = os.path.join(out_dir, f"BadBumps_fwdrev_{chip}.txt")
    with open(txt,"w") as f:
        f.write("Missing (col,row):\n")
        for col,row in coords["miss"]: f.write(f"{col},{row}\n")
        f.write("\nProblematic (col,row):\n")
        for col,row in coords["prob"]: f.write(f"{col},{row}\n")
    print("✓", txt)

# ─────────────── análisis por chip ───────────────
def analyse_chip(chip, mod, fwd, rev, cc, root_out, out_dir):


    chip_dir_path = f"Detector/Board_0/OpticalGroup_0/Hybrid_0/Chip_{chip}"
    dirs = chip_dir_path.split('/')
    chip_dir = root_out
    for d in dirs:
        if not chip_dir.GetDirectory(d):
            chip_dir = chip_dir.mkdir(d)
        else:
            chip_dir = chip_dir.GetDirectory(d)

    tags = { "thr": f"D_B(0)_O(0)_H(0)_Threshold2D_Chip({chip})",
             "noi": f"D_B(0)_O(0)_H(0)_Noise2D_Chip({chip})",
             "msk": f"D_B(0)_O(0)_H(0)_Masked2D_Chip({chip})" }

    h_thr_f = find_histogram(fwd , tags["thr"])
    h_thr_r = find_histogram(rev , tags["thr"])
    h_noi_f = find_histogram(fwd , tags["noi"])
    h_noi_r = find_histogram(rev , tags["noi"])
    h_mask  = find_histogram(cc  , tags["msk"])
    if None in (h_thr_f,h_thr_r,h_noi_f,h_noi_r,h_mask):
        print(f"Chip {chip}: falta un histograma → omitido"); return

    # 1-D shifts
    plot_shift_1d(h_thr_f,h_thr_r,"Threshold", THR_MISS, THR_PROB, out_dir,chip,root_out, chip_dir)
    plot_shift_1d(h_noi_f,h_noi_r,"Noise", NOI_MISS, NOI_PROB, out_dir,chip,root_out, chip_dir)

    # ΔThr / ΔNoise listas
    dThr,dNoi=[],[]
    nx,ny = h_thr_f.GetNbinsX(), h_thr_f.GetNbinsY()
    for ix in range(1,nx+1):
        for iy in range(1,ny+1):
            dThr.append(h_thr_f.GetBinContent(ix,iy)-h_thr_r.GetBinContent(ix,iy))
            dNoi.append(h_noi_f.GetBinContent(ix,iy)-h_noi_r.GetBinContent(ix,iy))
    plot_shift_2d(dThr,dNoi,out_dir,chip,root_out, chip_dir)

    #draw_summary(h_mask,dThr,dNoi,out_dir,chip,root_out)
    draw_summary_manual_mask(chip, mod, h_mask, dThr, dNoi, out_dir, root_out, chip_dir)
    
def draw_summary_manual_mask(chip, mod, h_mask_in, dThr, dNoi, out_dir, root_out, chip_dir):
    nx, ny = h_mask_in.GetNbinsX(), h_mask_in.GetNbinsY()
    h_miss = ROOT.TH2I("h_miss", "", nx, 0, nx, ny, 0, ny)
    h_prob = ROOT.TH2I("h_prob", "", nx, 0, nx, ny, 0, ny)
    h_mask = ROOT.TH2I("h_mask", "", nx, 0, nx, ny, 0, ny)

    coords = {"miss": [], "prob": []}
    for ix in range(1, nx + 1):
        for iy in range(1, ny + 1):
            if chip == 15 and ix > nx - 8 and mod==102:
                h_mask.SetBinContent(ix, iy, 1)
                continue
             
            masked = (h_mask.GetBinContent(ix, iy) != 0)    
            
            if masked:
                h_mask.SetBinContent(ix, iy, 1)
            else:
                cat = classify_pixel(dThr[(ix - 1) * ny + iy - 1], dNoi[(ix - 1) * ny + iy - 1], masked)
                if cat == 1:
                    h_miss.SetBinContent(ix, iy, 1)
                    coords["miss"].append((ix - 1, iy - 1))
                elif cat == 2:
                    h_prob.SetBinContent(ix, iy, 1)
                    coords["prob"].append((ix - 1, iy - 1))

    for h, c in ((h_miss, ROOT.kRed), (h_prob, ROOT.kOrange + 7), (h_mask, ROOT.kGreen + 2)):
        h.SetFillColor(c)
        h.SetStats(0)
        h.GetXaxis().SetTitle("Columns")
        h.GetYaxis().SetTitle("Rows")
        h.GetXaxis().SetTitleSize(34)
        h.GetXaxis().SetTitleFont(43)
        h.GetYaxis().SetTitleSize(34)
        h.GetYaxis().SetTitleFont(43)
        h.GetXaxis().SetLabelSize(0.04)
        h.GetYaxis().SetLabelSize(0.04)

    W, H_HIST, H_LEG = 1150, 800, 40
    canvas = ROOT.TCanvas(f"c_sum_{chip}", "", W, H_HIST + H_LEG)
    pad_hist = ROOT.TPad("pad_hist", "", 0.0, H_LEG / (H_HIST + H_LEG), 1.0, 1.0)
    pad_leg = ROOT.TPad("pad_leg", "", 0.0, 0.0, 1.0, H_LEG / (H_HIST + H_LEG))
    for p in (pad_hist, pad_leg):
        p.SetFillStyle(0)
        p.SetBorderSize(0)
        p.Draw()
    pad_hist.cd()
    
    
    
    h_miss.Draw("BOXF")
    h_prob.Draw("BOXF SAME")
    
    if h_mask.GetEntries() > 0:
        h_mask.Draw("BOXF SAME")
    
    
    pad_leg.cd()
    leg = ROOT.TLegend(0.10, 0.05, 0.90, 0.95)
    leg.SetNColumns(3)
    leg.SetBorderSize(1)
    leg.SetFillColor(0)
    leg.SetTextAlign(22)
    leg.SetTextSize(0.75)
    leg.AddEntry(h_miss, f"Missing ({len(coords['miss'])})", "f")
    leg.AddEntry(h_prob, f"Problematic ({len(coords['prob'])})", "f")
    if mod== 102:
        leg.AddEntry(h_mask, f"Masked (2688)" if chip == 15 else "Masked (0)", "f")
    leg.Draw()

    canvas.Update()
    png = os.path.join(out_dir, f"Fwrd_reverse_method_Chip({chip}).png")
    canvas.SaveAs(png)
    chip_dir.cd()
    chip_dir.WriteTObject(canvas, f"Fwrd_reverse_method_Chip({chip})")

    txt = os.path.join(out_dir, f"BadBumps_fwdrev_{chip}.txt")
    with open(txt, "w") as f:
        f.write("Missing (col,row):\n")
        for col, row in coords["miss"]:
            f.write(f"{col},{row}\n")
        f.write("\nProblematic (col,row):\n")
        for col, row in coords["prob"]:
            f.write(f"{col},{row}\n")
    print("✓", txt)

# ─────────────── main ────────────────────────────
def main():
    if len(sys.argv) < 5:
        print(__doc__); sys.exit(1)

    fwd_path, rev_path, cc_path = sys.argv[1:4]
    mod = sys.argv[4]
    out_dir = sys.argv[5] if len(sys.argv) > 5 else "FwdReverse_analysis"
    os.makedirs(out_dir, exist_ok=True)

    fwd = ROOT.TFile.Open(fwd_path,"READ")
    rev = ROOT.TFile.Open(rev_path,"READ")
    cc  = ROOT.TFile.Open(cc_path,"READ")
    if not all((fwd,rev,cc)):
        sys.exit("[ERROR] No se pudieron abrir los ROOT de entrada")

    root_out = ROOT.TFile(os.path.join(out_dir,"fwd_reverse_method.root"),"RECREATE")
    for chip in (15,14,13,12):
        analyse_chip(chip,mod,fwd,rev,cc,root_out,out_dir)

    root_out.Close(); fwd.Close(); rev.Close(); cc.Close()
    print("✔  Resultados completos en", out_dir)

if __name__ == "__main__":
    main()
