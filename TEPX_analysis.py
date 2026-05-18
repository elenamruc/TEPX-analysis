# =====================================================
# TEPX_analysis.py
# Author: Elena Muñoz
#
# This script just saves the plots obtained by the
# root files executing dirigent in png format.
# =====================================================

import ROOT
import os
import sys
import argparse
import re

# --- ROOT configuration ---
ROOT.gROOT.SetBatch(True)
ROOT.gStyle.SetOptStat(0)
ROOT.gStyle.SetNumberContours(255)
ROOT.gStyle.SetPalette(ROOT.kBird)
ROOT.gStyle.SetTextFont(43)
ROOT.gStyle.SetTitleFont(43, "XYZ")
ROOT.gStyle.SetLabelFont(43, "XYZ")
ROOT.gStyle.SetTitleSize(34, "XYZ")
ROOT.gStyle.SetLabelSize(0.04, "XYZ")

# --- Global list to keep references alive
STATS_BOXES = []

parser = argparse.ArgumentParser(description="Save plots from ROOT files in PNG format.")
parser.add_argument("root_dir", help="Path to directory containing ROOT files")
args = parser.parse_args()
root_dir = args.root_dir


def add_custom_stats(hist, x=0.3, y=0.3):
    """
    Create a ROOT-like stats display:
      - Title box (bold, centered)
      - Stats box (labels + values aligned in columns, no gap between boxes)
    """

    name = hist.GetName() if hasattr(hist, "GetName") else ""
    entries = hist.GetEntries()

    # Detect TH2
    is_th2 = isinstance(hist, ROOT.TH2)
    if is_th2:
        mean_x = hist.GetMean(1)
        mean_y = hist.GetMean(2)
        std_x = hist.GetStdDev(1)
        std_y = hist.GetStdDev(2)
    else:
        mean = hist.GetMean()
        stddev = hist.GetStdDev()

    # Extract title
    title = ""
    m = re.search(r"D_B\([^)]*\)_O\([^)]*\)_H\([^)]*\)_(.*?)_Chip", name)
    if m:
        title = m.group(1)
    elif "_Chip" in name:
        title = name.split("_Chip", 1)[0].split(")_")[-1]
    title = title.strip()

    # --- Geometry ---
    total_width, total_height = 0.2, 0.18
    title_height = 0.045
    x1, y2 = x, 1 - y
    x2 = x1 + total_width
    y1 = y2 - total_height

    # --- Title box ---
    title_box = ROOT.TPaveText(x1, y2 - title_height, x2, y2, "NDC")
    title_box.SetFillColor(ROOT.kWhite)
    title_box.SetFillStyle(1001)
    title_box.SetLineColor(ROOT.kGray+2)
    title_box.SetLineWidth(2)
    title_box.SetTextFont(62)
    title_box.SetTextSize(0.03)
    title_box.SetTextAlign(22)
    title_box.SetBorderSize(1)
    title_box.AddText(title if title else "Stats")

    # --- Stats box ---
    y2_stats = y2 - title_height  # no gap now
    stats_box = ROOT.TPaveText(x1, y1, x2, y2_stats, "NDC")
    stats_box.SetFillColor(ROOT.kWhite)
    stats_box.SetFillStyle(1001)
    stats_box.SetLineColor(ROOT.kGray+2)
    stats_box.SetLineWidth(2)
    stats_box.SetTextFont(42)
    stats_box.SetTextSize(0.03)
    stats_box.SetBorderSize(1)

    # Column X positions (in normalized box coords)
    label_x = 0.05
    value_x = 0.55

    # Build stats
    if is_th2:
        stats = [
            ("Entries", f"{int(entries)}"),
            ("Mean x",  f"{int(mean_x)}"),
            ("Mean y",  f"{mean_y:.3f}"),
            ("Std Dev x", f"{std_x:.3f}"),
            ("Std Dev y", f"{std_y:.3f}")
        ]
    else:
        stats = [
            ("Entries", f"{int(entries)}"),
            ("Mean",    f"{int(mean)}"),
            ("Std Dev", f"{stddev:.3f}")
        ]

    # --- Manual alignment: one line per row ---
    n = len(stats)
    line_height = 1.0 / n
    y_top = 0.92

    for i, (label, value) in enumerate(stats):
        y_pos = y_top - i * line_height

        # label
        t_label = stats_box.AddText(label)
        t_label.SetTextAlign(12)
        t_label.SetX(label_x)
        t_label.SetY(y_pos)

        # value (same Y, shifted X)
        t_value = stats_box.AddText(value)
        t_value.SetTextAlign(12)
        t_value.SetX(value_x)
        t_value.SetY(y_pos)

    # Draw both boxes
    title_box.Draw("same")
    stats_box.Draw("same")

    # Keep alive
    STATS_BOXES.extend([title_box, stats_box])

def save_canvas_or_hist(obj, chip_name, object_name, output_dir, show_title=True):
    """
    Save TCanvas or TH1/TH2 objects with high resolution and custom stats.
    """
    save_name = f"{chip_name}_{object_name}.png".replace("/", "_")
    save_path = os.path.join(output_dir, save_name)

    is_special = any(key in object_name for key in ["SCurves", "SCurve", "ThrNoise2D"])
    ROOT.gStyle.SetPalette(ROOT.kRainBow if is_special else ROOT.kBird)

    def clean_pad(pad):
        """
        Remove legends recursively and darken TGaxis.
        """
        subprims = pad.GetListOfPrimitives()
        to_delete = []
        for prim in subprims:
            if prim.InheritsFrom("TPad"):
                clean_pad(prim)
            elif prim.InheritsFrom("TGaxis"):
                prim.SetLineColor(ROOT.kBlack)
                prim.SetLabelColor(ROOT.kBlack)
                prim.SetTitleColor(ROOT.kBlack)
            elif prim.InheritsFrom("TLegend"):
                to_delete.append(prim)
        for item in to_delete:
            subprims.Remove(item)
        pad.Modified()
        pad.Update()

    # --- Case 1: TCanvas ---
    if obj.InheritsFrom("TCanvas"):
        print(f"Processing canvas: {object_name}")

        found_hist = None

        def find_histograms(pad):
            nonlocal found_hist
            for prim in pad.GetListOfPrimitives():
                if prim.InheritsFrom("TPad"):
                    find_histograms(prim)
                elif prim.InheritsFrom("TAxis"):
                    prim.SetLineColor(ROOT.kBlack)
                    prim.SetLabelColor(ROOT.kBlack)
                    prim.SetTitleColor(ROOT.kBlack)

                elif prim.InheritsFrom("TH1"):
                    found_hist = prim

        find_histograms(obj)



        if found_hist:
            # Create new canvas
            c = ROOT.TCanvas("c", "c", 1150, 800)
            draw_opt = "COLZ" if found_hist.InheritsFrom("TH2") else "HIST"
            found_hist.SetStats(False)

            if not show_title:
                found_hist.SetTitle("")

            if is_special and found_hist.InheritsFrom("TH2"):
                ROOT.gPad.SetLogz(True)

            is_3d = any(opt in draw_opt for opt in ["SURF", "LEGO", "ISO", "BOX"])

            # --- Adjust margins ---
            if not is_3d:
                #c.SetTopMargin(0.13 if show_title else 0.08)
                #c.SetBottomMargin(0.12)
                c.SetLeftMargin(0.10)
                c.SetRightMargin(0.15)

            # Detect existing top axes
            original_axes = [
                prim for prim in obj.GetListOfPrimitives() if prim.InheritsFrom("TGaxis")
            ]
            has_existing_top_axis = any(
                abs(ax.GetY1() - ax.GetY2()) < 1e-6 and ax.GetY1() > 0.9 for ax in original_axes
            )

            xaxis = found_hist.GetXaxis()
            yaxis = found_hist.GetYaxis()
            zaxis = found_hist.GetZaxis() if found_hist.InheritsFrom("TH2") else None

            for ax in [xaxis, yaxis] + ([zaxis] if zaxis else []):
                ax.SetTitleOffset(1.4 if ax == yaxis else 1.2)
            if zaxis:
                zaxis.SetTitleOffset(1.8)

            # Draw histogram
            found_hist.Draw(draw_opt)
            c.Update()

            # --- Optional Gaussian fit depending on histogram name ---
            fit_function = None

            if isinstance(found_hist, ROOT.TH1):
                hname = found_hist.GetName()

                # Fit Noise
                if "Noise1D" in hname:
                    fr = found_hist.Fit("gaus", "S+", "", 19, 27)
                    fit_function = found_hist.GetFunction("gaus")
                    if fit_function:
                        fit_function.SetLineColor(ROOT.kRed)
                        fit_function.SetLineWidth(3)

                # Fit Threshold
                if "Threshold1D" in hname:
                    fr = found_hist.Fit("gaus", "S+", "", 360, 440)
                    fit_function = found_hist.GetFunction("gaus")
                    if fit_function:
                        fit_function.SetLineColor(ROOT.kRed)
                        fit_function.SetLineWidth(3)


            # --- Clone top axes only if they exist ---
            if has_existing_top_axis:
                for ax in original_axes:
                    ax_clone = ax.Clone()
                    ax_clone.SetLineColor(ROOT.kBlack)       # axis in black
                    ax_clone.SetLabelColor(ROOT.kBlack)
                    ax_clone.SetTitleColor(ROOT.kBlack)
                    ax_clone.Draw()
                    if "AXIS_LIST" not in globals():
                        globals()["AXIS_LIST"] = []
                    AXIS_LIST.append(ax_clone)

            # --- Adjust colorbar (avoid misalignment or excessive width) ---
            palette = found_hist.FindObject("palette")
            if palette:
                palette.SetX1NDC(0.855)
                palette.SetX2NDC(0.895)
                palette.SetY1NDC(0.10)
                palette.SetY2NDC(0.90)

                c.Update()

                # Get the axis directly from the TPaletteAxis object
                try:
                    zaxis = palette.GetAxis() if hasattr(palette, "GetAxis") else None
                    if not zaxis and hasattr(palette, "GetZaxis"):
                        zaxis = palette.GetZaxis()
                    if not zaxis and hasattr(palette, "GetHistogram"):
                        zaxis = palette.GetHistogram().GetZaxis()
                except Exception:
                    zaxis = None

                if any(k in object_name for k in ["SCurves", "SCurve", "ThrNoise2D"]):
                    z_label = "Number of pixels"
                else:
                    z_label = ""    

                latex = ROOT.TLatex()
                latex.SetTextFont(42)
                latex.SetTextSize(0.04)
                latex.SetTextAngle(90)
                latex.SetTextAlign(22) 
                latex.DrawLatexNDC(0.965, 0.80, z_label)

                STATS_BOXES.append(latex) 
                c.Modified()
                c.Update()


            title_primitives = [
                prim for prim in obj.GetListOfPrimitives()
                if (prim.InheritsFrom("TPaveText") or prim.InheritsFrom("TLatex"))
            ]
            has_original_title = len(title_primitives) > 0

            if has_original_title:
                if show_title:
                    # If the user wants to hide it, remove it from the original canvas
                    for prim in title_primitives:
                        title_clone = prim.Clone()
                        title_clone.Draw()
                        STATS_BOXES.append(title_clone)
            # --- Add statistics box ---
            if "Noise1D" in found_hist.GetName():
                add_custom_stats(found_hist, x=0.6, y=0.12)
            else:
                add_custom_stats(found_hist, x=0.12, y=0.12)

            # --- Save ---
            c.Modified()
            c.Update()
            c.SaveAs(save_path)
            c.Close()
            print(f"Saved canvas: {save_path}")

        
    # --- Case 2: TH1/TH2 directly ---
    if obj.InheritsFrom("TH1"):
        c = ROOT.TCanvas("c", "c", 1150, 800)
        draw_opt = "COLZ" if obj.InheritsFrom("TH2") else "HIST"
        obj.SetStats(False)
        if is_special and obj.InheritsFrom("TH2"):
            ROOT.gPad.SetLogz(True)
        obj.Draw(draw_opt)
        ROOT.gPad.Update()
        add_custom_stats(obj, x=0.12, y=0.12)
        c.Update()
        c.SaveAs(save_path)
        c.Close()
        print(f"Saved direct histogram with custom stats: {save_path}")


def explore_directory(directory, chip_name="", output_dir="."):
    """
    Recursively explore ROOT directories and save canvases or histograms.
    """
    for key in directory.GetListOfKeys():
        obj = key.ReadObj()
        if not obj:
            continue
        name = obj.GetName()
        if obj.InheritsFrom("TDirectory"):
            if "Chip_" in name:
                chip_name = name
                print(f"\nOpening {chip_name}")
            explore_directory(obj, chip_name, output_dir)
        elif obj.InheritsFrom("TCanvas") or obj.InheritsFrom("TH1"):
            save_canvas_or_hist(obj, chip_name, name, output_dir, show_title=False)

def main():
    # --- Main loop: accept either one ROOT file or a directory with ROOT files ---

    input_path = root_dir

    if os.path.isfile(input_path):
        root_files = [input_path]
        base_output_dir = os.path.dirname(input_path)

    elif os.path.isdir(input_path):
        root_files = []

        for filename in sorted(os.listdir(input_path)):

            # Skip hidden/system files, especially macOS ._ files
            if filename.startswith("."):
                continue

            if not filename.endswith(".root"):
                continue

            root_files.append(os.path.join(input_path, filename))

        base_output_dir = input_path

    else:
        print(f"Error: path does not exist: {input_path}")
        sys.exit(1)


    for filepath in root_files:
        filename = os.path.basename(filepath)
        base_name = os.path.splitext(filename)[0]

        output_dir = os.path.join(base_output_dir, f"plots_{base_name}")
        os.makedirs(output_dir, exist_ok=True)

        print(f"\nOpening file: {filename}")
        print(f"→ Output folder: {output_dir}")

        try:
            f = ROOT.TFile.Open(filepath)
        except OSError:
            print(f"Skipping invalid ROOT file: {filename}")
            continue

        if not f or f.IsZombie():
            print(f"Could not open file: {filename}")
            continue

        explore_directory(f, chip_name="", output_dir=output_dir)
        f.Close()

        print(f"All plots for {filename} saved in {output_dir}")

    print("\nAll ROOT files processed successfully.")


if __name__ == "__main__":
    main()
