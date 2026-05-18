import ROOT
import sys
import os
from array import array

def process_directory_by_name(directory, target_name, rute=""):
    """
    Busca recursivamente en el TFile un TCanvas cuyo nombre sea target_name.
    Cuando lo encuentra, devuelve el primer histograma que aparezca en su lista de primitivas.
    """
    for key in directory.GetListOfKeys():
        obj = key.ReadObj()
        if obj.IsA().InheritsFrom(ROOT.TDirectory.Class()):
            new_path = f"{rute}/{obj.GetName()}" if rute else obj.GetName()
            result = process_directory_by_name(obj, target_name, new_path)
            if result:
                return result
        elif obj.IsA().InheritsFrom(ROOT.TCanvas.Class()) and obj.GetName() == target_name:
            print(f"Found Canvas: {obj.GetName()}")
            for prim in obj.GetListOfPrimitives():
                if prim.InheritsFrom(ROOT.TH1.Class()):
                    print(f"Found Histogram: {prim.GetName()}")
                    return prim
    return None 
    
def draw_Hitsperpixel(h2, canvas, output_folder, mod_id, name_suffix=""):
    canvas.Clear(); canvas.SetLogy(False)
    canvas.cd() 
    canvas.SetLeftMargin(0.1)
    canvas.SetRightMargin(0.17)
    
    h2.SetName(f"Hits per Pixel Map ({mod_id})") 
    h2.SetTitle("")
    h2.Draw("COLZ")
    
    # Configure the size and font of the axis titles
    h2.SetZTitle("Hits Per Pixel")
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
    
    ROOT.gPad.Update()
    
    # Ajusta la posición de la barra de colores
    pal = h2.GetListOfFunctions().FindObject("palette")
    if pal:
        pal.SetX1NDC(0.83); pal.SetX2NDC(0.87)
        pal.SetY1NDC(canvas.GetBottomMargin())
        pal.SetY2NDC(1 - canvas.GetTopMargin()) 
        
    # Ajusta la caja de estadísticas
    stats = h2.GetListOfFunctions().FindObject("stats")
    if stats:
        top_margin = canvas.GetTopMargin()
        right_margin = canvas.GetRightMargin()
        stats_height = 0.15
        stats_width = 0.2    
        x1_ndc = 1 - right_margin - stats_width
        x2_ndc = 1 - right_margin
        y2_ndc = 1 - top_margin
        y1_ndc = y2_ndc - stats_height
        stats.SetY1NDC(y1_ndc-0.06)
        stats.SetY2NDC(y2_ndc-0.03)
        stats.SetX1NDC(x1_ndc-0.03)
        stats.SetX2NDC(x2_ndc-0.03)
        canvas.Modified() 
    canvas.Update()
    
    file_path = os.path.join(output_folder, f"{h2.GetName()}{name_suffix}.png")
    canvas.SaveAs(file_path)
    print(f"Histogram saved: {file_path}")

def draw_missing_prob(h_hits, h_mask, h_tot, out_dir, mod_id,
                      suffix="", show_mask=True, legend=True):
    """
    Clasifica los píxeles en Missing / Hits < 200 / Masked y los dibuja
    en un canvas 1150 × 840 con la leyenda horizontal en la banda inferior.
    También guarda un .txt con las coordenadas de los píxeles malos.
    """
    canvas = ROOT.TCanvas(f"c_missing_{mod_id}", "", 1150, 800)
    for m in (canvas.SetTopMargin, canvas.SetBottomMargin,
              canvas.SetLeftMargin, canvas.SetRightMargin):
        m(0.10)
    if None in (h_hits, h_mask, h_tot):
        print("[WARN] draw_missing_prob: falta algún histograma"); return

    # ───── reclasificación ──────────────────────────────────────
    nx, ny = h_hits.GetNbinsX(), h_hits.GetNbinsY()
    h_miss = ROOT.TH2I("h_miss","",nx,0,nx,ny,0,ny)
    h_prob = ROOT.TH2I("h_prob","",nx,0,nx,ny,0,ny)
    h_msk  = ROOT.TH2I("h_msk" ,"",nx,0,nx,ny,0,ny)

    n_miss=n_prob=n_msk=0
    miss_pos, prob_pos = [],[]

    for ix in range(1,nx+1):
        for iy in range(1,ny+1):
            occ = h_hits.GetBinContent(ix,iy)
            tot = h_tot .GetBinContent(ix,iy)
            if h_mask.GetBinContent(ix,iy)!=0:
                h_msk.SetBinContent(ix,iy,1); n_msk+=1; continue
            if occ<200 and tot<1:
                h_miss.SetBinContent(ix,iy,1); n_miss+=1; miss_pos.append((ix-1,iy-1))
            elif occ<200:
                h_prob.SetBinContent(ix,iy,1); n_prob+=1; prob_pos.append((ix-1,iy-1))

    # ───── estilos ──────────────────────────────────────────────
    h_miss.SetFillColor(ROOT.kRed)
    h_prob.SetFillColor(ROOT.kBlue)
    h_msk .SetFillColor(ROOT.kGreen+2)
    for h in (h_miss,h_prob,h_msk):
        h.SetStats(0)
        h.GetXaxis().SetTitle("Columns")
        h.GetYaxis().SetTitle("Rows")
        #h.SetTitle(f"Missing Bumps - Xray (I-102 Mod {mod_id})")
        h.SetTitle(f"")

    # ───── canvas + pads ────────────────────────────────────────
    W,H_H,H_L = 1150,800,40
    cname     = f"c_miss_{mod_id}{suffix}"
    canv      = ROOT.TCanvas(cname,"",W,H_H+H_L)

    frac = H_L/float(H_H+H_L)
    pH = ROOT.TPad(f"padH_{cname}","",0,frac,1,1)
    pL = ROOT.TPad(f"padL_{cname}","",0,0  ,1,frac)
    for p in (pH,pL): p.SetFillStyle(0); p.SetBorderSize(0)
    pH.Draw(); pL.Draw()

    # histograma
    pH.cd()
    if show_mask: h_msk.Draw("BOXF")
    h_miss.Draw("BOXF SAME")
    h_prob.Draw("BOXF SAME")

    # leyenda
    if legend:
        pL.cd()
        leg = ROOT.TLegend(0.10,0.05,0.90,0.95)
        leg.SetNColumns(3); leg.SetBorderSize(1); leg.SetFillColor(0)
        leg.SetTextAlign(22); leg.SetTextSize(0.75)
        leg.AddEntry(h_miss,f"Missing ({n_miss})","f")
        leg.AddEntry(h_prob,f"Hits < 200 ({n_prob})","f")
        if show_mask:
            leg.AddEntry(h_msk ,f"Masked ({n_msk})"   ,"f")
        leg.Draw()

    # ───── guardar png y txt ────────────────────────────────────
    canv.SetLeftMargin(0.12)
    canv.SetRightMargin(0.1)
    canv.Update()
    png = os.path.join(out_dir,f"Xray_badbump_Chip({mod_id}){suffix}.png")
    canv.SaveAs(png)
    print("Saved", png)

    if legend:
        txt = os.path.join(out_dir,f"BadBumps_Xray_{mod_id}.txt")
        with open(txt,"w") as f:
            f.write("Missing (col,row):\n")
            for c,r in miss_pos: f.write(f"{c},{r}\n")
            f.write("\nProblematic (col,row):\n")
            for c,r in prob_pos: f.write(f"{c},{r}\n")
        print("Positions written to", txt)

    # opcional: escribir el canvas en un ROOT externo
    canvas_name = f"Xray_badbump_Chip({mod_id})"
    canv.Write(canvas_name)
    print(f"Canvas written to ROOT file as {canvas_name}")

def draw_z_histograms(prim, masked_hist, modID, output_folder, log_scale=False):
    """
    Dibuja histogramas 1D de los valores de hits per pixel en escala lineal y logarítmica.
    """
    canvas = ROOT.TCanvas(f"c_z_{modID}", "", 1150, 800)
    for m in (canvas.SetTopMargin, canvas.SetBottomMargin, canvas.SetRightMargin):
        m(0.10)
        
    canvas.SetLeftMargin(0.15)
    
    n_bins_x = prim.GetNbinsX()
    n_bins_y = prim.GetNbinsY()
    z_values_all = []
    z_values_unmasked = []
    for i in range(1, n_bins_x + 1):
        for j in range(1, n_bins_y + 1):
            z_value = prim.GetBinContent(i, j)
            if masked_hist.GetBinContent(i, j) == 0:
                z_values_unmasked.append(z_value)
            z_values_all.append(z_value)
            
    for z_values, label in [(z_values_all, "all"), (z_values_unmasked, "unmasked")]:
        hist_z_values = ROOT.TH1F(f"Hits per Pixel 1D ({modID}) ({label})", 
                                  f";Hits per Pixel;Entries",
                                  100, 0, 100000)
        canvas.SetTitle(f"HitsPerPixel1D_{label}")
        
        for z in z_values:
            hist_z_values.Fill(z)
        hist_z_values.SetLineWidth(2)
        canvas.cd()
        canvas.SetLogy(1 if log_scale else 0)
        hist_z_values.Draw("HIST")
        canvas.Update()

        stats = hist_z_values.GetListOfFunctions().FindObject("stats")
        if stats:
            top_margin = canvas.GetTopMargin()
            right_margin = canvas.GetRightMargin()
            stats_height = 0.15
            stats_width = 0.2    
            x1_ndc = 1 - right_margin - stats_width
            x2_ndc = 1 - right_margin
            y2_ndc = 1 - top_margin
            y1_ndc = y2_ndc - stats_height
            stats.SetY1NDC(y1_ndc-0.03)
            stats.SetY2NDC(y2_ndc-0.03)
            stats.SetX1NDC(x1_ndc-0.03)
            stats.SetX2NDC(x2_ndc-0.03)
            
        canvas.Modified()
        canvas.Update()
    
        suffix = "log" if log_scale else "linear"
        png    = os.path.join(output_folder,
                 f"hits_per_pixel_1D_{label}_{suffix}_Chip({modID}).png")

        canvas.SaveAs(png)
        print("Saved", png)

        if not log_scale:        
            canvas_name = f"hits_per_pixel_1D_{label}_Chip({modID})"
            canvas.Write(canvas_name)
            print(f"Canvas written to ROOT file as {canvas_name}")

def save_histograms(root_file, masked_file):
    """
    Procesa los mod_ID 15, 14, 13 y 12 a partir de:
      - root_file: archivo ROOT principal con histogramas de hits per pixel y ToT.
      - masked_file: archivo ROOT que contiene en carpetas ("Mod15", etc.) el histograma de masked pixels
        denominado "Masked_Pixels_Map"
      
    Para cada mod_ID se:
      - Obtiene el histograma masked correspondiente del masked_file.
      - Busca en el root_file los histogramas de PixelAlive y ToT correspondientes a ese mod_ID.
      - Llama a las funciones de dibujo (draw_Hitsperpixel, draw_missing_prob, draw_z_histograms) para crear
        los canvas y guardarlos (tanto en formato imagen como en el output ROOT file).
      - En el output ROOT file se agrupan los resultados en carpetas llamadas "Mod15", "Mod14", etc.
    """
    import ROOT, os

    # Lista de mod_ID a procesar
    mod_ID_list = ["15", "14", "13", "12"]

    # Obtiene el nombre base del archivo principal para usarlo en el directorio de salida.
    base_name = os.path.basename(root_file)
    root_name = os.path.splitext(base_name)[0]
    # Directorio para guardar las imágenes de salida.
    output_folder = os.path.join(os.getcwd(), "Xray_method_analysis")
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    # Abre los archivos ROOT de entrada.
    file = ROOT.TFile.Open(root_file, "READ")
    masked = ROOT.TFile.Open(masked_file, "READ")
    if not file or not file.IsOpen():
        print("Error al abrir", root_file)
        return
    if not masked or not masked.IsOpen():
        print("Error al abrir", masked_file)
        return

    # Crea el archivo ROOT de salida donde se escribirán todos los canvas.
    output_root_path = os.path.join(output_folder, "xray_histperpixel.root")
    output_root_file = ROOT.TFile(output_root_path, "RECREATE")

    # Opciones de estilo global
    ROOT.gStyle.SetOptStat(1)
    ROOT.gStyle.SetTitleSize(34, "xy")
    ROOT.gStyle.SetTitleFont(43, "xy")
    ROOT.gStyle.SetLabelSize(0.04, "xy")

    # Se crea un canvas general que se reutiliza (puedes crear nuevos canvas para cada dibujo si lo prefieres).
    canvas = ROOT.TCanvas("canvas", "canvas", 1150, 800)
    canvas.SetTopMargin(0.08)
    canvas.SetBottomMargin(0.1)
    canvas.SetLeftMargin(0.15)
    canvas.SetRightMargin(0.15)
    
    

    # Procesa cada mod_ID
    for mod_ID in mod_ID_list:
        print("Procesando mod_ID:", mod_ID)
        # Obtiene el histograma masked: se asume que en masked_file existe un directorio "Mod<mod_ID>"
        chip_dir_path = f"Detector/Board_0/OpticalGroup_0/Hybrid_0/Chip_{mod_ID}"
        mod_dir_masked = masked.GetDirectory(chip_dir_path)
        if not mod_dir_masked:
            print(f"No se encontró la carpeta {chip_dir_path} en masked_file.")
            continue

        masked_hist = mod_dir_masked.Get(f"Masked_Pixels_Map_Chip({mod_ID})")
        if not masked_hist:
            print(f"No se encontró 'Masked_Pixels_Map_Chip({mod_ID})' en {chip_dir_path}")
            continue
        
        
        

        # Buscar en el root_file los histogramas para este mod_ID.
        # Se utiliza la función process_directory_by_name para buscar el histograma de PixelAlive:
        prim_hits = process_directory_by_name(file, f"D_B(0)_O(0)_H(0)_PixelAlive_Chip({mod_ID})")
        # Y el histograma de ToT:
        tot_hist = process_directory_by_name(file, f"D_B(0)_O(0)_H(0)_ToT2D_Chip({mod_ID})")
        if not prim_hits:
            print("No se encontró histograma válido para mod_ID", mod_ID)
            continue

        # Ajustes básicos
        prim_hits.SetLineWidth(2)
        prim_hits.GetXaxis().SetTitleOffset(1)
        prim_hits.GetYaxis().SetTitleOffset(1.8)
        prim_hits.Scale(1e8)  

        # Crear (o acceder) a una carpeta en el output ROOT file para este mod_ID.
        
        dirs = chip_dir_path.split("/")
        mod_dir = output_root_file
        for d in dirs:
            if not mod_dir.GetDirectory(d):
                mod_dir = mod_dir.mkdir(d)
            else:
                mod_dir = mod_dir.GetDirectory(d)
        mod_dir.cd()


        draw_Hitsperpixel(prim_hits, canvas, output_folder, mod_ID, f"_Hist_{mod_ID}")
        canvas.Write(f"HitsPerPixel_Chip({mod_ID})")
       
        # Clonar para los diferentes dibujos.
        prim_clone_for_masked = prim_hits.Clone("prim_clone_for_masked")
        prim_clone_for_unmasked = prim_hits.Clone("prim_clone_for_unmasked")

        draw_missing_prob(prim_clone_for_masked, masked_hist, tot_hist, output_folder, mod_ID, f"_legend", show_mask=True, legend=True)
        # Si deseas también las versiones sin leyenda:
        draw_missing_prob(prim_clone_for_masked, masked_hist, tot_hist, output_folder, mod_ID, f"_nolegend", show_mask=True, legend=False)

        draw_z_histograms(prim_clone_for_unmasked, masked_hist, mod_ID, output_folder, log_scale=False)
        draw_z_histograms(prim_clone_for_unmasked, masked_hist, mod_ID, output_folder, log_scale=True)
        
    file.Close()
    masked.Close()
    output_root_file.Close()
    print("Todos los histogramas han sido escritos en:", output_root_path)
    
    
    
if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Uso: python script.py root_file.root masked_file.root")
        sys.exit(1)

    root_file = sys.argv[1]
    masked_file = sys.argv[2]
    
    save_histograms(root_file, masked_file)
