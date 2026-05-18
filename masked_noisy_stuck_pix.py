import ROOT
import sys
import os

def read_masked_positions(filename):
    """
    Reads a file and extracts positions where pixels are masked. These positions
    are expected to be listed under lines starting with 'ENABLE', with each
    pixel's status ('0' for masked) listed in comma-separated values.
    """
    with open(filename) as f:
        lines = f.readlines()
    
    masked_positions = set()
    i = 0  # Row counter
    for line in lines:
        if line.startswith("ENABLE"):
            enable_values = line.split()[1].split(",")
            for j, value in enumerate(enable_values):
                if value == "0":  # Check if the pixel is masked
                    masked_positions.add((i, j))
            i += 1
    return masked_positions

def compare_masked_positions(filemasked1, filemasked2):
    """
    Compares the masked positions between two different files and returns the positions
    that are unique to the second file.
    """
    masked_positions1 = read_masked_positions(filemasked1)
    masked_positions2 = read_masked_positions(filemasked2)
    return masked_positions2 - masked_positions1  # Set difference

def create_histogram(masked_positions, title, filename):
    """
    Creates and saves a ROOT histogram of masked positions.
    """
    # Initialize histogram with dimensions for a typical CMOS sensor
    hist = ROOT.TH2F(f"{title}", "", 432, 0, 432, 336, 0, 336)
    for pos in masked_positions:
        hist.Fill(*pos)  # Fill histogram at positions
        
    hist.SetFillColor(ROOT.kRed)
    hist.SetMarkerColor(ROOT.kRed)
    hist.SetLineColor(ROOT.kRed)

    hist.SetStats(1)  # Enable statistics box to display histogram info
    c = ROOT.TCanvas("c", title, 1150, 800)
    c.SetLeftMargin(0.12)
    c.SetRightMargin(0.1)
    c.SetBottomMargin(0.1)
    hist.Draw()  # Draw the histogram
    
    # Set the axis labels
    hist.GetXaxis().SetTitle("Column")
    hist.GetYaxis().SetTitle("Row")
  
    hist.GetXaxis().SetTitleSize(34)
    hist.GetXaxis().SetTitleFont(43)
    hist.GetYaxis().SetTitleSize(34)
    hist.GetYaxis().SetTitleFont(43)
    hist.GetXaxis().SetLabelSize(0.04) 
    hist.GetYaxis().SetLabelSize(0.04)  
    
    ROOT.gStyle.SetPalette(1)  # Set color palette for the histogram
    c.SaveAs(f"{filename}.png")  # Save the canvas as a PNG image
    
    hist.Write(f"D_B(0)_O(0)_H(0)_{title.replace(' ', '_')}_Chip({chip})")
    
    return c, hist

def main():
    """
    Main function to process masked pixel data and generate histograms.
    """
    if len(sys.argv) != 4:
        print("Uso: python script.py <masked.txt> <noise_prefix> <pixelalive_prefix>")
        print("Ejemplo: python script.py CMSIT_RD53B.txt Results/Run000014_CMSIT_RD53B_v Results/Run000016_CMSIT_RD53B_v")
        sys.exit(1)

    f_prefix      = sys.argv[1]
    noise_prefix  = sys.argv[2]  
    alive_prefix  = sys.argv[3]


    out_dir = "masked_noisy_stuck"
    os.makedirs(out_dir, exist_ok=True)
    root_file = ROOT.TFile(os.path.join(out_dir, "masked_noisy_stuck.root"), "RECREATE")

    for chip in [12, 13, 14, 15]:
        v = 15 - chip
        f_masked  = f"{f_prefix}{v}.txt"
        noise_scan  = f"{noise_prefix}{v}.txt"
        pixel_alive = f"{alive_prefix}{v}.txt"

        print(f"[Mod {chip}] Processing:")
        print(f" - Noise scan:   {noise_scan}")
        print(f" - Pixel alive:  {pixel_alive}")

        masked_positions = read_masked_positions(f_masked)
        noisy_positions  = read_masked_positions(noise_scan)
        stuck_positions  = compare_masked_positions(noise_scan, pixel_alive)

        chip_dir_path = f"Detector/Board_0/OpticalGroup_0/Hybrid_0/Chip_{chip}"
        dirs = chip_dir_path.split("/")
        mod_dir = root_file
        for d in dirs:
            if not mod_dir.GetDirectory(d):
                mod_dir = mod_dir.mkdir(d)
            else:
                mod_dir = mod_dir.GetDirectory(d)
        mod_dir.cd()

        for data, label in [
            (masked_positions, "Masked"),
            (noisy_positions,  "Noisy"),
            (stuck_positions,  "Stuck")
        ]:
            canvas, hist = create_histogram(data, f"{label} Pixels Mod{chip}", f"{label}_pixels_{chip}")
            canvas.SaveAs(os.path.join(mod_dir_path, f"{label.lower()}_pixels_mod{chip}.png"))
            canvas.Write(f"D_B(0)_O(0)_H(0)_{label}_Pixels_Chip({chip})")

    root_file.Close()


if __name__ == "__main__":
    main()



    

