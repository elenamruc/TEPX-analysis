
import ROOT
import sys
import os

def process_file(file_name):
    """
    Lee el archivo de texto y llena un histograma 2D (Masked Pixels Map).
    Se asume que el archivo contiene líneas que comienzan con "ENABLE" seguidas de los valores separados por comas.
    """
    # Lee el contenido del archivo
    with open(file_name) as f:
        lines = f.readlines()
    
    # Crea el histograma; se asumen dimensiones 432 x 336.
    hist = ROOT.TH2F("Masked_Pixels_Map", "Masked Pixels", 432, 0, 432, 336, 0, 336)
    
    # Extrae los datos
    data = []
    i = 0
    for line in lines:
        if line.startswith("ENABLE"):
            # Se extraen los valores y se almacenan en un diccionario
            enable_values = line.split()[1].split(",")
            data.append({f"ENABLE_{i}": enable_values})
            i += 1
    
    # Rellena el histograma: se llena el bin (i, j) si el correspondiente valor ENABLE es "0"
    for i in range(len(data)):
        for j in range(len(data[i][f"ENABLE_{i}"])):
            if data[i][f"ENABLE_{i}"][j] == "0":
                hist.Fill(i, j)
    
    # Se deja activada la cajita de estadísticas (1 = se muestra)
    hist.SetStats(1)
    
    return hist

def draw_and_save_histogram(hist, mod_ID, out_img_name):
    """
    Dibuja el histograma en un canvas, define márgenes y títulos, y lo guarda como imagen.
    """
    # Create the canvas
    c = ROOT.TCanvas("c", "Masked Pixels", 800, 600)
    
    # Set the margins
    c.SetLeftMargin(0.12)
    c.SetRightMargin(0.12)
    c.SetBottomMargin(0.12)
    c.SetTopMargin(0.12)
    
    # Draw the histogram with a color palette
    hist.Draw()
    
    # Set the title and axis labels
    hist.SetTitle("Masked Pixels")
    hist.GetXaxis().SetTitle("Column")
    hist.GetYaxis().SetTitle("Row")
    
    ROOT.gStyle.SetPalette(1)
    
    # Guarda la imagen en formato PNG
    c.SaveAs(out_img_name)
    
    return c

def main(file_names):
    """
    Procesa una lista de 4 archivos de texto. Para cada archivo:
      - Se asocia un mod_ID fijo en el orden: 15, 14, 13 y 12.
      - Se lee el archivo y se genera su histograma.
      - Se dibuja y guarda la imagen del histograma (con el sufijo _{mod_ID}).
      - Se escribe el histograma en un único archivo ROOT común, guardándolo
        dentro de una carpeta (TDirectory) de nombre "Mod{mod_ID}".
    """
    # Lista de mod_ID en el orden fijo (primero 15, segundo 14, tercero 13 y cuarto 12)
    mod_IDs = ["15", "14", "13", "12"]
    
    # Directorio de salida (se utiliza el directorio actual; cámbialo si lo necesitas)
    output_dir = os.getcwd()
    # Archivo ROOT de salida único (sin mod_ID en el nombre)
    root_file_name = "masked_pix_tunning.root"
    output_root_file = ROOT.TFile(root_file_name, "RECREATE")
    
    # Se espera que file_names tenga exactamente 4 archivos
    if len(file_names) != 4:
        print("Error: Se deben pasar exactamente 4 archivos de texto.")
        sys.exit(1)
    
    for idx, file_name in enumerate(file_names):
        mod_ID = mod_IDs[idx]
        # Obtiene el nombre base del archivo de texto para usarlo en el nombre de la imagen
        base = os.path.splitext(os.path.basename(file_name))[0]
        
        # Procesa el archivo para obtener su histograma
        hist = process_file(file_name)
        
        # Renombra el histograma: 
        new_hist_name = f"Masked_Pixels_Map_Chip({mod_ID})"
        hist.SetName(new_hist_name)
        
        # Guarda la imagen del histograma; el nombre incluye el mod_ID
        out_img_name = os.path.join(output_dir, f"Masked_Pixels_Map_Chip({mod_ID})_{base}.png")
        draw_and_save_histogram(hist, mod_ID, out_img_name)
        print(f"Imagen guardada: {out_img_name}")
        
        # Crea (o accede) a una carpeta dentro del archivo ROOT para este mod_ID
        chip_dir_path = f"Detector/Board_0/OpticalGroup_0/Hybrid_0/Chip_{mod_ID}"
        dirs = chip_dir_path.split("/")
        current_dir = output_root_file
        for d in dirs:
            if not current_dir.GetDirectory(d):
                current_dir = current_dir.mkdir(d)
            else:
                current_dir = current_dir.GetDirectory(d)
        current_dir.cd()



        hist.Write(new_hist_name)
    
    output_root_file.Close()
    print(f"Todos los histogramas han sido escritos en: {root_file_name}")

if __name__ == "__main__":
    # Se esperan 4 archivos de texto como argumentos.
    if len(sys.argv) != 2:
        print("Uso: python script.py file")
        sys.exit(1)
    
    base_name = sys.argv[1]
    name, ext = os.path.splitext(base_name)

    # Generar los nombres: archivo_v_1.txt, archivo_v_2.txt, etc.
    file_names = [f"{name}_{i}.txt" for i in range(0, 4)]
    main(file_names)
    

