# Micro-CT analysis

This folder contains the retinal-layer segmentation model for zebrafish eye micro-CT images, a notebook to run it in Python, and a notebook to measure photoreceptor-layer (PRL) thickness from the segmentation masks.

All commands below are run from this `mCT/` folder.

## Folder structure

```
mCT/
    README.md
    models/
        LICENSE                        CC BY 4.0 (model files)
        arivis/
            model.czann                model, new format
            model.czmodel              model, legacy format
    inference/
        run_arivis_model.ipynb         run the model in Python (Jupyter)
        run_arivis_model.py            same, from the command line
        environment.yml                conda environment: zf-arivis-model
    thickness/
        prl_thickness_polar_maps.ipynb PRL thickness measurement and polar maps
        environment.yml                conda environment: zf-prl-thickness
```

## 1. Segmentation model

A semantic-segmentation model (EfficientNet-B0 encoder, U-Net decoder) trained on ZEISS arivis Cloud. Both files contain the same trained model, exported for different software versions:

| File | Format | Software |
|---|---|---|
| `model.czann` | New | ZEN blue 3.5+, ZEN core 3.4+, arivis Pro 3.6+ |
| `model.czmodel` | Legacy | ZEN blue 3.4, ZEN core 3.3 |

**Input:** 16-bit grayscale images, processed as 192 × 192 px tiles with a 24 px overlap.

**Output:** one label per pixel, from seven classes:

| Label | Class | Description |
|---|---|---|
| 1 | background | not used in the analysis |
| 2 | GCL | ganglion cell layer |
| 3 | INL | inner nuclear layer |
| 4 | IPL | inner plexiform layer |
| 5 | LENS | lens |
| 6 | ON | optic nerve (annotated only where present) |
| 7 | ONL | photoreceptor layer (PRL), see below |

The class labelled `ONL` during annotation corresponds to the full photoreceptor layer (PRL) as defined in the paper: photoreceptor cell bodies, inner segments and outer segments.

Only the LENS and PRL classes are used in the downstream morphometry.

### Running the model

**Recommended: ZEISS arivis / ZEN.** All segmentation masks used in the paper were generated with this model in arivis Cloud, which is the recommended way to reproduce them. Load `models/arivis/model.czann` (or `model.czmodel` for older software versions) in arivis Cloud, arivis Pro or ZEN, and apply it to the images.

**Alternative: Python.** For users without access to ZEISS software, `inference/run_arivis_model.ipynb` runs the model with [ONNX Runtime](https://onnxruntime.ai/). Its output can differ slightly from arivis, mainly at boundaries between layers.

```
cd inference
conda env create -f environment.yml
conda activate zf-arivis-model
jupyter lab
```

Open `run_arivis_model.ipynb`, set the paths in the **Settings** cell, and run all cells.

| Setting | Description |
|---|---|
| `MODEL_PATH` | path to `model.czann` or `model.czmodel` (default: `../models/arivis/model.czann`) |
| `INPUT_PATH` | a `.tif`/`.tiff` file or a folder of them; each file can be a 2D slice or a 3D stack |
| `OUTPUT_DIR` | output folder |
| `SAVE_CLASSES` | classes to also save as separate 0/255 masks, e.g. `["ONL", "LENS"]` |

Relative paths are relative to the `inference/` folder. Outputs are:

- `labels/<name>.tif`: a label image with values 1–7, as in the table above
- `<input>_<CLASS>/<name>.tif`: a 0/255 mask for each class listed in `SAVE_CLASSES`

The same can be run from the command line:

```
python run_arivis_model.py --input path/to/images --output predictions --classes ONL LENS
```

## 2. PRL thickness analysis

`thickness/prl_thickness_polar_maps.ipynb` measures PRL thickness across the eye from the PRL and lens masks. It then plots the group-mean thickness as a polar map.

```
cd thickness
conda env create -f environment.yml
conda activate zf-prl-thickness
jupyter lab
```

### Input

The notebook expects 360 rotational slices per eye, 1° apart. Masks must use 0 for background and 255 for foreground:

```
thickness/data/
└── <group>_C/                                   e.g. WT5dpf_C, mutant1_C
    ├── <group>_raw/<fish_ID>/                   raw micro-CT slices (.tiff); one folder per fish
    ├── <group>_cleaned_ONL/<fish_ID>_ONL/       PRL mask slices
    └── <group>_cleaned_lens/<fish_ID>_lens/     lens mask slices
```

Slices are expected at 350 × 200 px. Landscape slices are transposed, smaller slices are zero-padded, and larger slices are cropped. Fish IDs are taken from the folder names in `<group>_raw`. For the group averages, each fish ID must contain its group name.

fish IDs only need to contain the pattern used in the combine cell (e.g. WT), not the full group name

The voxel size is 1 µm (isotropic), so thickness is reported in µm.

### Settings

| Setting | Description |
|---|---|
| `DATA_DIR` | folder containing the `<group>_C` folders (default: `data`) |
| `OUTPUT_DIR` | output folder (default: `outputs`) |
| `CENTRE_METHOD` | how the eye centre is found: `"lens"` (from the lens mask, default) or `"raw"` (from the raw image) |
| `conditions` | groups to process, e.g. `['WT5dpf', 'mutant1']` |

### Method

1. **Eye centre.** With `"lens"`, the centre is the average vertical midpoint of the lens, measured column by column from the left edge of the first lens slice. With `"raw"`, it is the midpoint between the two highest intensity peaks along the left-edge column of the first raw slice.
2. **Thickness.** On each of the 360 slices, 180 rays (1° apart) are cast from the eye centre, and PRL voxels are counted along each ray. This gives a 360 × 180 thickness map per fish.
3. **Group maps.** The per-fish maps are averaged per group and shown as a polar contour map. Two rings of 10° sector bars show the mean thickness (inner ring) and the 99th-percentile thickness - near-maximum thickness (outer ring). Values below 5 µm are excluded from the map and the sector bars.

### Output

- `outputs/data/<fish_ID>.npy`: per-fish 360 × 180 thickness map (µm)
- `outputs/img/<fish_ID>.png`: per-fish quality-control figure
- `outputs/polar/<group>.png`: group-mean polar map

## Licence

- **Code** (`inference/`, `thickness/`): MIT licence, see the repository's [`LICENSE`](../LICENSE).
- **Segmentation model** (`models/`): [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/), see [`models/LICENSE`](models/LICENSE).
