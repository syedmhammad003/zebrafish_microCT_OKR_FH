"""
Run the arivis Cloud retinal-layer model on TIFF images, without ZEISS software.

The .czann / .czmodel files are zip archives containing a standard ONNX model and a
metadata file. This script reads the model with ONNX Runtime, splits each 2D image
into overlapping 192 x 192 tiles, predicts every tile and blends the overlaps.

Note
    The segmentation masks published with the paper were generated in arivis Cloud.
    To reproduce them exactly, run the model in arivis Cloud, arivis Pro or ZEN.
    This script is an alternative for users without ZEISS software; its output can
    differ slightly from arivis, mainly at boundaries between layers.

Input
    A single .tif/.tiff file, or a folder of them. Each file can be a single 2D slice
    or a 3D stack (slices along the first axis); every slice is segmented in 2D.
    Images should be 16-bit grayscale, as used for training.

Output (written to --output)
    labels/<name>.tif               label image, values 1-7 (same label values as ZEN):
                                    1 background, 2 GCL, 3 INL, 4 IPL, 5 LENS, 6 ON, 7 ONL
    <name>_<CLASS>/<name>.tif       optional 0/255 masks for the classes given in --classes

Examples
    python run_arivis_model.py --input data/fish1.tif --output predictions
    python run_arivis_model.py --input data/fish1_slices/ --output predictions \
        --classes ONL LENS
"""

import argparse
import json
import re
import sys
import warnings
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

import numpy as np
import onnxruntime as ort
import tifffile

DEFAULT_MODEL = Path(__file__).resolve().parents[1] / "models" / "arivis" / "model.czann"
TIFF_SUFFIXES = {".tif", ".tiff"}


# --------------------------------------------------------------------------------------
# Model loading
# --------------------------------------------------------------------------------------
def load_model(model_path):
    """Read the ONNX model and metadata from a .czann or .czmodel file.

    Returns (session, info) where info holds tile size, overlap, class names and
    the input scaling the model expects.
    """
    model_path = Path(model_path)
    with zipfile.ZipFile(model_path) as z:
        names = z.namelist()
        model_name = next(n for n in names if n.endswith(".model"))
        model_bytes = z.read(model_name)

        json_files = [n for n in names if n.endswith(".json")]
        xml_files = [n for n in names if n.endswith(".xml")]
        if json_files:                                   # new format (.czann)
            meta = json.loads(z.read(json_files[0]))
            tile = tuple(meta["InputShape"][:2])
            overlap = tuple(meta["MinOverlap"])
            classes = meta["Classes"]
        elif xml_files:                                  # legacy format (.czmodel)
            root = ET.fromstring(z.read(xml_files[0]))
            border = int(root.findtext("BorderSize"))
            overlap = (border, border)
            items = sorted(root.find("TrainingClasses"), key=lambda i: int(i.get("LabelValue")))
            classes = [i.get("Name") for i in items]
            tile = None                                  # read from the ONNX input below
        else:
            raise ValueError(f"No metadata (.json or .xml) found in {model_path}")

    session = ort.InferenceSession(model_bytes, providers=ort.get_available_providers())
    inp = session.get_inputs()[0]
    if tile is None:
        tile = tuple(inp.shape[1:3])

    info = {
        "tile": tile,
        "overlap": overlap,
        "classes": classes,
        "input_name": inp.name,
        "scale_to_unit": expects_unit_range(model_bytes, model_path),
    }
    return session, info


def expects_unit_range(model_bytes, model_path):
    """True if the model expects 16-bit intensities scaled to 0-1, False for raw 0-65535.

    Both files contain the same trained network but with different built-in
    normalisation: .czann subtracts ~0.37 (0-1 scale), .czmodel subtracts ~24251
    (raw 16-bit scale). The shift constant is read from the graph; if it cannot be
    found, the file extension is used instead.
    """
    try:
        import onnx
        from onnx import numpy_helper

        graph = onnx.load_from_string(model_bytes).graph
        values = {t.name: numpy_helper.to_array(t) for t in graph.initializer}
        for node in graph.node:
            if node.op_type == "Constant":
                values[node.output[0]] = numpy_helper.to_array(node.attribute[0].t)
        for node in graph.node:
            if node.op_type == "Add" and "shift" in node.name.lower():
                shift = [values[i] for i in node.input if i in values]
                if shift:
                    return abs(float(np.ravel(shift[0])[0])) < 10
    except ImportError:
        pass
    return Path(model_path).suffix.lower() == ".czann"


# --------------------------------------------------------------------------------------
# Tiled prediction
# --------------------------------------------------------------------------------------
def tile_starts(length, tile, overlap):
    """Tile start positions spread evenly so the tiles exactly cover `length`,
    with neighbouring tiles overlapping by at least `overlap` pixels."""
    if length <= tile:
        return [0]
    n = int(np.ceil((length - overlap) / (tile - overlap)))
    return [int(round(i * (length - tile) / (n - 1))) for i in range(n)]


def blend_weights(th, tw):
    """Linear weights, highest at the tile centre and lowest at its edges."""
    wy = np.minimum(np.arange(th) + 1, th - np.arange(th))
    wx = np.minimum(np.arange(tw) + 1, tw - np.arange(tw))
    return np.outer(wy, wx).astype(np.float32)[..., None]


def predict_slice(image, session, info, batch_size=16):
    """Segment one 2D image. Returns class probabilities, shape (rows, cols, n_classes).

    The image is covered by an evenly spaced grid of tiles that overlap by at least the
    model's overlap (24 px), without padding the image edges. Where tiles overlap, their
    predictions are averaged with linear weights that favour each tile's centre.
    Images smaller than one tile are mirror-padded up to the tile size.
    """
    th, tw = info["tile"]
    oh, ow = info["overlap"]
    rows, cols = image.shape

    x = image.astype(np.float32)
    if info["scale_to_unit"]:
        x = x / 65535.0
    pad_r, pad_c = max(0, th - rows), max(0, tw - cols)
    if pad_r or pad_c:
        x = np.pad(x, ((0, pad_r), (0, pad_c)), mode="reflect")
    H, W = x.shape

    coords = [(y, c) for y in tile_starts(H, th, oh) for c in tile_starts(W, tw, ow)]
    weights = blend_weights(th, tw)
    acc = np.zeros((H, W, len(info["classes"])), np.float32)
    wsum = np.zeros((H, W, 1), np.float32)
    for b in range(0, len(coords), batch_size):
        batch = coords[b:b + batch_size]
        tiles = np.stack([x[y:y + th, c:c + tw] for y, c in batch])[..., None]
        probs = session.run(None, {info["input_name"]: tiles})[0]
        for (y, c), p in zip(batch, probs):
            acc[y:y + th, c:c + tw] += p * weights
            wsum[y:y + th, c:c + tw] += weights
    return (acc / wsum)[:rows, :cols]


def check_image(image, path):
    if image.ndim not in (2, 3):
        raise ValueError(f"{path}: expected a 2D image or 3D stack, got shape {image.shape}")
    if image.ndim == 3 and image.shape[-1] in (3, 4) and image.shape[0] > 4:
        raise ValueError(f"{path}: looks like an RGB image {image.shape}; the model expects grayscale")
    if image.dtype != np.uint16:
        warnings.warn(
            f"{path}: dtype is {image.dtype}, but the model was trained on 16-bit images. "
            "Values are used as they are, which may give poor results."
        )


# --------------------------------------------------------------------------------------
# Main
# --------------------------------------------------------------------------------------
def natural_key(path):
    return [int(t) if t.isdigit() else t.lower() for t in re.split(r"(\d+)", Path(path).name)]


def list_inputs(path):
    path = Path(path)
    if path.is_file():
        return [path]
    files = sorted((p for p in path.iterdir() if p.suffix.lower() in TIFF_SUFFIXES), key=natural_key)
    if not files:
        raise FileNotFoundError(f"No .tif/.tiff files found in {path}")
    return files


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--input", required=True, help="TIFF file or folder of TIFF files")
    parser.add_argument("--output", required=True, help="output folder")
    parser.add_argument("--model", default=str(DEFAULT_MODEL), help="path to model.czann or model.czmodel")
    parser.add_argument("--classes", nargs="*", default=[],
                        help="also save 0/255 masks for these classes, e.g. ONL LENS")
    parser.add_argument("--batch-size", type=int, default=16)
    args = parser.parse_args(argv)

    session, info = load_model(args.model)
    classes = info["classes"]
    unknown = [c for c in args.classes if c not in classes]
    if unknown:
        parser.error(f"unknown class(es) {unknown}; available: {classes}")

    print(f"Model: {Path(args.model).name} | tile {info['tile']} | overlap {info['overlap']} | "
          f"input scaled to 0-1: {info['scale_to_unit']}")
    print(f"Classes (label 1-{len(classes)}): {classes}")

    files = list_inputs(args.input)

    out_dir = Path(args.output)
    (out_dir / "labels").mkdir(parents=True, exist_ok=True)

    for f in files:
        image = tifffile.imread(f)
        check_image(image, f)
        stack = image[None] if image.ndim == 2 else image

        labels = np.stack([
            predict_slice(s, session, info, args.batch_size).argmax(-1).astype(np.uint8) + 1
            for s in stack
        ])
        if image.ndim == 2:
            labels = labels[0]

        tifffile.imwrite(out_dir / "labels" / f"{f.stem}.tif", labels, compression="zlib")
        for name in args.classes:
            mask = (labels == classes.index(name) + 1).astype(np.uint8) * 255
            folder = out_dir / f"{Path(args.input).stem}_{name}"
            folder.mkdir(exist_ok=True)
            tifffile.imwrite(folder / f"{f.stem}.tif", mask, compression="zlib")
        print(f"  {f.name}: {stack.shape[0]} slice(s) done")


if __name__ == "__main__":
    sys.exit(main())
