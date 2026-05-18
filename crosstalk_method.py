#!/usr/bin/env python3
import ROOT, sys, os
from array import array


ROOT.gStyle.SetOptStat(1)
ROOT.gStyle.SetTitleSize(34, "xy")
ROOT.gStyle.SetTitleFont(43, "xy")
ROOT.gStyle.SetLabelSize(0.04, "xy")
    
    
# ────────────────────────────────────────────────────────────────
# 0. util para buscar histogramas/canvas por nombre
# ────────────────────────────────────────────────────────────────
def find_histogram(tdir, target_substr):
    for key in tdir.GetListOfKeys():
        obj = key.ReadObj()
        if obj.InheritsFrom(ROOT.TH1.Class()) and target_substr in obj.GetName():
            return obj
        if obj.InheritsFrom(ROOT.TCanvas.Class()) and target_substr in obj.GetName():
            for prim in obj.GetListOfPrimitives():
                if prim.InheritsFrom(ROOT.TH1.Class()):
                    return prim
        if obj.InheritsFrom(ROOT.TDirectory.Class()):
            out = find_histogram(obj, target_substr)
            if out: return out
    return None

# ────────────────────────────────────────────────────────────────
# 1. dibujo PixelAlive 2-D
# ────────────────────────────────────────────────────────────────
def draw_pixelalive(th2, canvas, out_dir, mod_dir, tag, mod):
    if th2 is None: 
        print(f"[WARN] no PixelAlive {tag}")
        return  
    canvas.Clear(); canvas.SetLogy(False)
    canvas.cd() 
    canvas.SetLeftMargin(0.1)
    canvas.SetRightMargin(0.15)

    # Set margins for the canvas to ensure all elements are visible
    canvas.SetLeftMargin(0.12)
    canvas.SetRightMargin(0.1)

    
    th2.SetName(f"Pixel Alive {tag} ({mod})") 
    th2.SetTitle("")
    th2.Draw("COLZ")
    
    # Configure the size and font of the axis titles
    th2.SetZTitle("Pixel Efficiency")
    th2.GetXaxis().SetTitleSize(34)  
    th2.GetXaxis().SetTitleFont(43) 
    th2.GetXaxis().SetTitleOffset(1.8)
    th2.GetXaxis().SetLabelSize(0.04)
    th2.GetYaxis().SetTitleSize(34)  
    th2.GetYaxis().SetTitleFont(43) 
    th2.GetYaxis().SetTitleOffset(1.8)
    th2.GetYaxis().SetLabelSize(0.04)
    th2.GetZaxis().SetTitleSize(34)  
    th2.GetZaxis().SetTitleFont(43) 
    th2.GetZaxis().SetTitleOffset(1.8)
    th2.GetZaxis().SetLabelSize(0.04)
    
    ROOT.gPad.Update()
    
    # Ajusta la posición de la barra de colores
    pal = th2.GetListOfFunctions().FindObject("palette")
    if pal:
        pal.SetX1NDC(0.83); pal.SetX2NDC(0.87)
        pal.SetY1NDC(canvas.GetBottomMargin())
        pal.SetY2NDC(1 - canvas.GetTopMargin())     
    
    canvas.Modified(); canvas.Update()
    canvas.SaveAs(os.path.join(out_dir, f"PixelAlive_{tag}_Chip({mod}).png"))
    mod_dir.cd(); canvas.Write(f"PixelAlive_{tag}_Chip({mod})")

# ────────────────────────────────────────────────────────────────
# 2. mapa resumen con leyenda en banda inferior
# ────────────────────────────────────────────────────────────────
def make_summary_map(th2_cpl, th2_unc, mask,
                     canvas_hist, out_dir, mod_dir, modID,
                     low=0.10, high=0.98, scale=1.0):

    if None in (th2_cpl, th2_unc, mask):
        print(f"[WARN] SummaryMap: histogramas faltantes para módulo {modID}")
        return

    # ───── clasificamos píxeles ─────────────────────────────────────
    nx, ny = th2_cpl.GetNbinsX(), th2_cpl.GetNbinsY()
    h_mask = ROOT.TH2I("h_mask","",nx,0,nx,ny,0,ny)
    h_miss = ROOT.TH2I("h_miss","",nx,0,nx,ny,0,ny)
    h_prob = ROOT.TH2I("h_prob","",nx,0,nx,ny,0,ny)
    n_mask = n_miss = n_prob = 0


    miss_pos, prob_pos = [],[]
    
    for ix in range(1, nx+1):
        for iy in range(1, ny+1):
            if mask.GetBinContent(ix, iy) != 0:
                h_mask.SetBinContent(ix, iy, 1);  n_mask += 1;  continue
            e1 = th2_cpl.GetBinContent(ix, iy) * scale
            e2 = th2_unc.GetBinContent(ix, iy) * scale
            if e1 < low and e2 < low:
                h_miss.SetBinContent(ix, iy, 2);  n_miss += 1; miss_pos.append((ix-1,iy-1))
            elif not (e1 >= high or e2 >= high):
                h_prob.SetBinContent(ix, iy, 3);  n_prob += 1; prob_pos.append((ix-1,iy-1))

    # Colores y ejes
    h_mask.SetFillColor(ROOT.kGreen+2)
    h_prob.SetFillColor(ROOT.kOrange+7)
    h_miss.SetFillColor(ROOT.kRed)
    for h in (h_mask, h_prob, h_miss):
        h.SetStats(0)
        h.GetXaxis().SetTitle("Columns")
        h.GetYaxis().SetTitle("Rows")
        #h.SetTitle(f"Missing Bumps - CrossTalk (I-102 Mod {modID})")

    # ───── canvas 1150×840  (800 px histo + 40 px leyenda) ────────
    W, H_HIST, H_LEG = 1150, 800, 40
    canvas = ROOT.TCanvas(f"c_sum_{modID}", "", W, H_HIST + H_LEG)

    frac_leg  = H_LEG  / float(H_HIST + H_LEG)   
    frac_hist = 1.0 - frac_leg                  

    #  ➜  Pad del histograma ocupa la franja *superior*
    pad_hist = ROOT.TPad("pad_hist", "", 0.0, frac_leg, 1.0, 1.0)
    #  ➜  Pad de la leyenda ocupa la franja *inferior*
    pad_leg  = ROOT.TPad("pad_leg" , "", 0.0, 0.0,       1.0, frac_leg)
    pad_leg .SetFillStyle(0); pad_leg .SetBorderSize(0)
    pad_hist.SetFillStyle(0); pad_hist.SetBorderSize(0)

    pad_hist.Draw(); pad_leg.Draw()

    # ───── dibujamos el mapa en el pad del histograma ───────────────
    pad_hist.cd()
    pad_hist.SetTopMargin   (0.10)
    pad_hist.SetRightMargin (0.10)
    pad_hist.SetLeftMargin  (0.12)
    pad_hist.SetBottomMargin(0.12)

    h_mask.SetMinimum(0)
    h_mask.SetMaximum(1)
    h_mask.SetContour(1)
    h_mask.SetMarkerSize(1)

    h_mask.SetFillColor(ROOT.kGreen + 2)   # masked
    h_miss.SetFillColor(ROOT.kRed)         # missing bump
    h_prob.SetFillColor(ROOT.kOrange + 7)  # problematic

    h_mask.SetLineWidth(0)
    h_miss.SetLineWidth(0)
    h_prob.SetLineWidth(0)

    pad_hist.cd()
    pad_hist.SetFixedAspectRatio()
    pad_hist.cd()

    h_mask.Draw("BOX")
    h_miss.Draw("BOX SAME")
    h_prob.Draw("BOX SAME")

    # ───── leyenda horizontal en el pad inferior ────────────────────
    pad_leg.cd()
    leg = ROOT.TLegend(0.10, 0.15, 0.9, 1)   # ocupa casi todo el pad
    leg.SetNColumns(3)
    leg.SetBorderSize(1)
    leg.SetFillColor(0)
    leg.SetTextAlign(22)
    leg.SetTextSize(0.75)        # tamaño relativo al pad_le- g (0–1)

    for h, txt in ((h_miss, f"Missing ({n_miss})"),
                   (h_prob, f"Problematic ({n_prob})"),
                   (h_mask, f"Masked ({n_mask})")):
        entry = leg.AddEntry(h, txt, "f")
        entry.SetLineColor(0) 
        entry.SetLineWidth(0)
        entry.SetMarkerSize(0.5)

    leg.Draw()
    pad_leg.Modified(); pad_leg.Update()

    # ───── guardar ──────────────────────────────────────────────────
    canvas.Update()
    png_path = os.path.join(out_dir, f"crostalk_badbump_Chip({modID}).png")
    canvas.SaveAs(png_path)
    mod_dir.cd(); canvas.Write(f"crostalk_badbump_Chip({modID})")
    
    
    txt = os.path.join(out_dir,f"BadBumps_CrossTalk_{modID}.txt")
    with open(txt,"w") as f:
        f.write("Missing (col,row):\n")
        for c,r in miss_pos: f.write(f"{c},{r}\n")
        f.write("\nProblematic (col,row):\n")
        for c,r in prob_pos: f.write(f"{c},{r}\n")
    print("Positions written to", txt)

    print(f"[Mod {modID}] Masked={n_mask} | Problematic={n_prob} | Missing={n_miss}")

# ────────────────────────────────────────────────────────────────
# 3. TH2 → TH1
# ────────────────────────────────────────────────────────────────
def eff_hist(th2, name, tag, mod, out_dir, mod_dir, scale=1.0, n_bins=100):
    if not th2 or not th2.InheritsFrom(ROOT.TH2.Class()):
        print(f"[WARN] Cannot make efficiency hist for {tag} (Mod {mod})")
        return

    # Crear histograma 1D desde el TH2
    h1 = ROOT.TH1F(name, ";Efficiency;Number of Pixels", n_bins, 0.0, 1.00001)
    for ix in range(1, th2.GetNbinsX()+1):
        for iy in range(1, th2.GetNbinsY()+1):
            h1.Fill(th2.GetBinContent(ix, iy) * scale)

    # Canvas uniforme
    
    canvas = ROOT.TCanvas(f"eff_{tag}_{mod}", "", 1150, 800)
    for m in (canvas.SetTopMargin, canvas.SetBottomMargin, canvas.SetRightMargin):
        m(0.10)
    canvas.SetLeftMargin(0.12)

    # Estilo del histograma
    h1.SetLineWidth(2)
    h1.SetStats(1)
    
    # Opciones de estilo global
    ROOT.gStyle.SetOptStat(1)
    ROOT.gStyle.SetTitleSize(34, "xy")
    ROOT.gStyle.SetTitleFont(43, "xy")
    ROOT.gStyle.SetLabelSize(0.04, "xy")
    h1.GetYaxis().SetTitleOffset(1.2)

    # Dibujo
    canvas.cd()
    canvas.SetLogy(1)
    h1.Draw("HIST")

    # Líneas verticales
    ymax = h1.GetMaximum()
    l10 = ROOT.TLine(0.10, 0, 0.10, ymax)
    l98 = ROOT.TLine(0.98, 0, 0.98, ymax)
    for l in (l10, l98):
        l.SetLineWidth(3)
    l10.SetLineColor(ROOT.kRed)
    l98.SetLineColor(ROOT.kOrange+7)
    l10.Draw(); l98.Draw()

    # Stats box (posición fija)
    canvas.Update()
    stats = h1.GetListOfFunctions().FindObject("stats")
    if stats:
        top_margin = canvas.GetTopMargin()
        right_margin = canvas.GetRightMargin()
        stats_height = 0.15
        stats_width = 0.2
        x1_ndc = 1 - right_margin - stats_width
        x2_ndc = 1 - right_margin
        y2_ndc = 1 - top_margin
        y1_ndc = y2_ndc - stats_height
        stats.SetY1NDC(y1_ndc - 0.03)
        stats.SetY2NDC(y2_ndc - 0.03)
        stats.SetX1NDC(x1_ndc - 0.03)
        stats.SetX2NDC(x2_ndc - 0.03)
        canvas.Modified()

    canvas.Update()
    canvas.SaveAs(os.path.join(out_dir, f"eff_{tag}_Chip({mod}).png"))
    mod_dir.cd(); canvas.Write(f"eff_{tag}_Chip({mod})")
    print(f"✓ eff_{tag}_{mod}.png saved")

# ────────────────────────────────────────────────────────────────
# 4. análisis de un módulo
# ────────────────────────────────────────────────────────────────
def analyse_module(f_cpl,f_unc,f_msk,mod,root_out,canvas,
                   low=0.10,high=0.98,scale=1.0,out_dir="Crosstalk_method_analysis"):

    chip_dir_path = f"Detector/Board_0/OpticalGroup_0/Hybrid_0/Chip_{mod}"
    dirs = chip_dir_path.split('/')
    mod_dir = root_out
    for d in dirs:
        if not mod_dir.GetDirectory(d):
            mod_dir = mod_dir.mkdir(d)
        else:
            mod_dir = mod_dir.GetDirectory(d)

    tag = f"PixelAlive_Chip({mod})"
    tag_mask = f"Masked2D_Chip({mod})"
    h2_cpl = find_histogram(f_cpl,tag)
    h2_unc = find_histogram(f_unc,tag)
    h2_mask= find_histogram(f_msk,tag_mask)

    # 1-D
    for h2, tag2 in ((h2_cpl, "coupled"), (h2_unc, "uncoupled")):
        eff_hist(h2, f"eff_{tag2}", tag2, mod, out_dir, mod_dir, scale=scale)
       

    # mapas
    make_summary_map(h2_cpl,h2_unc,h2_mask,canvas,out_dir,mod_dir,mod,
                     low,high,scale)

    draw_pixelalive(h2_cpl,canvas,out_dir,mod_dir,"coupled", mod)
    draw_pixelalive(h2_unc,canvas,out_dir,mod_dir,"uncoupled", mod)

# ────────────────────────────────────────────────────────────────
# 5. main
# ────────────────────────────────────────────────────────────────
if __name__=="__main__":
    if len(sys.argv)<4:
        print("Uso: python script.py masked.root coupled.root uncoupled.root [12 13 14 15]")
        sys.exit(1)

    masked_root, coupled_root, uncoupled_root = sys.argv[1:4]
    mods = ([12,13,14,15] if len(sys.argv)==4 else list(map(int,sys.argv[4:])))

    out_dir = "Crosstalk_method_analysis"; os.makedirs(out_dir,exist_ok=True)
    root_out = ROOT.TFile(os.path.join(out_dir,"crosstalk_method.root"),"RECREATE")

    canvas = ROOT.TCanvas("c","",1150,800)          # canvas “normal” (se reutiliza)
    for m in (canvas.SetTopMargin, canvas.SetBottomMargin,
              canvas.SetLeftMargin, canvas.SetRightMargin): m(0.10)

    f_cpl = ROOT.TFile.Open(coupled_root ,"READ")
    f_unc = ROOT.TFile.Open(uncoupled_root,"READ")
    f_msk = ROOT.TFile.Open(masked_root  ,"READ")

    for mod in mods:
        analyse_module(f_cpl,f_unc,f_msk,mod,root_out,canvas,
                       low=0.10,high=0.98,scale=1.0,out_dir=out_dir)

    root_out.Close(); f_cpl.Close(); f_unc.Close(); f_msk.Close()
    print("Completed analysis – results in:", out_dir)

