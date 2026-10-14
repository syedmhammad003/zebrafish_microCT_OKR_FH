# Optokinetic response (OKR) analysis

This folder contains the eye-tracking model and scripts used to analyse the optokinetic response (OKR) of zebrafish larvae.

The pipeline has three steps:

1. **Eye tracking.** Larval eye movements are tracked in OKR videos with a DeepLabCut model.
2. **Conversion to eye angles.** `zebrafish_DLC2SMR.ipynb` converts the tracked coordinates into left- and right-eye angles and adds the stimulus protocol.
3. **OKR analysis in Spike2.** Slow-phase velocity is measured in Spike2.

## Folder structure

```
okr/
    README.md
    dlc_model/                     DeepLabCut model (config.yaml + trained network), CC BY 4.0
    protocol/
        trialsLoop_5dpf.csv        stimulus protocol
    zebrafish_DLC2SMR.ipynb        DeepLabCut coordinates → eye angles
```

## 1. Eye tracking with DeepLabCut

The DeepLabCut model was developed and described in:

> Patil M, Birchall A, Syed H, Rodwell V, Yoon H-J, Norton WHJ, Thomas MG. A Deep Learning Approach to Measure Visual Function in Zebrafish. *Biology* 14, 663 (2025). https://doi.org/10.3390/biology14060663

It was built with DeepLabCut:

> Mathis A, Mamidanna P, Cury KM, et al. DeepLabCut: markerless pose estimation of user-defined body parts with deep learning. *Nature Neuroscience* 21, 1281–1289 (2018). https://doi.org/10.1038/s41593-018-0209-y

Please cite both papers if you use the model.

It is a DeepLabCut (v2.3.9) model with a ResNet-50 backbone. It tracks six points: two on each eye (`LE1`, `LE2`, `RE1`, `RE2`) and two on the body midline (`MID1`, `MID2`).

### Install

```
conda create -n zf-okr python=3.10
conda activate zf-okr
pip install "deeplabcut[gui,tf]==2.3.9"
pip install jupyterlab
```

Use DeepLabCut 2.3.9. Later versions use a different deep-learning engine by default and may not load this model.
DeepLabCut is distributed under the GNU LGPL v3 and is installed separately; it is not included in this repository.

### Set the model location

Before first use, open `dlc_model/config.yaml` in a text editor and set `project_path` to the full path of the `dlc_model` folder on your computer, for example:

```yaml
project_path: C:/Users/<you>/<repository>/okr/dlc_model
```

Save the file. DeepLabCut uses this path to find the trained network.

### Video requirements

- Recorded at **30 frames per second**
- **One larva per video**, with both eyes in view
- **Trimmed to start at the onset of the stimulus**, so that the first frame corresponds to the start of the protocol

### Analyse videos

1. Start DeepLabCut: `python -m deeplabcut`
2. Click **Load project** and select `dlc_model/config.yaml`.
3. Open the **Analyze videos** tab.
4. Select the videos to analyse.
5. Tick **Save result(s) as csv**.
6. Click **Analyze videos**.

DeepLabCut writes one `.csv` file per video, next to the video. These CSV files are the input for the next step.

## 2. Conversion to eye angles

`zebrafish_DLC2SMR.ipynb` converts the DeepLabCut coordinates into eye angles (in degrees) for each eye, and aligns them with the stimulus protocol.

Start Jupyter in the `zf-okr` environment (`jupyter lab`), open the notebook and set the paths at the top of the first cell:

| Setting | Description |
|---|---|
| `input_folder` | folder containing the DeepLabCut `.csv` files |
| `protocol_path` | stimulus protocol, `protocol/trialsLoop_5dpf.csv` |
| `output_folder` | output folder (default: a `results` subfolder of `input_folder`) |
| `output_prefix` | prefix added to the output file names (default: `R`) |

In the second cell, set `directory` to the same results folder.

### Output

- **First cell:** one `.csv` file per larva with the columns `Time` (s), `LE_deg`, `RE_deg` (left- and right-eye angle, degrees), and the stimulus `duration`, `orientation` and `frequency` at each frame.
- **Second cell:** `master_results.csv`, combining the eye angles of all larvae in one file.

### Stimulus protocol

`protocol/trialsLoop_5dpf.csv` describes the stimulus sequence (125 s in total):

| Epoch | Duration | Direction | Spatial frequency (cycles/degree) | Speed |
|---|---|---|---|---|
| Stationary | 5 s | none | 0.067 | 0 deg/s |
| Moving | 6 × 10 s | clockwise | 0.022, 0.044, 0.067, 0.089, 0.111, 0.156 | 15 deg/s |
| Moving | 6 × 10 s | anticlockwise | 0.022, 0.044, 0.067, 0.089, 0.111, 0.156 | 15 deg/s |

## 3. OKR analysis in Spike2

Slow-phase velocity was measured in Spike2 (Cambridge Electronic Design, CED) using CED's OKR analysis script (`OKR_03`, Spike2 v10.17 or later), which is available from CED.

1. In Spike2, import the per-larva `.csv` file with **File → Import**.
2. Run the OKR script and use **Mark States** to mark the stimulus epochs from the `duration`, `orientation` and `frequency` channels.
3. Use **Analyse** to detect the saccades and measure the slow-phase velocity of each eye.
4. Use **Table** to export the results.

## Licence and citation

- **Code** (`zebrafish_DLC2SMR.ipynb`): MIT licence, see the repository's [`LICENSE`](../LICENSE).
- **DeepLabCut model** (`dlc_model/`): [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/), see [`dlc_model/LICENSE`](dlc_model/LICENSE). Please cite Patil et al. (2025) and Mathis et al. (2018) above.
