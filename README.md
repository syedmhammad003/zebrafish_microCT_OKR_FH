# zebrafish_microCT_OKR_FH

# Zebrafish retinal-layer segmentation, PRL thickness and optokinetic response analysis

It contains two independent parts, each with its own instructions and software setup:

| Folder | Contents | Instructions |
|---|---|---|
| `mCT/` | Micro-CT analysis: a retinal-layer segmentation model, a notebook to run it in Python, and a notebook to measure photoreceptor-layer (PRL) thickness | [`mCT/README.md`](mCT/README.md) |
| `okr/` | Optokinetic response (OKR) analysis: a DeepLabCut eye-tracking model and a notebook to convert tracked coordinates into eye angles | [`okr/README.md`](okr/README.md) |

## Repository structure

```
README.md
LICENSE                                MIT (code)
CITATION.cff
mCT/                                   micro-CT analysis
    README.md
    models/arivis/                     segmentation model (CC BY 4.0)
    inference/                         run the model in Python
    thickness/                         PRL thickness measurement and polar maps
okr/                                   optokinetic response analysis
    README.md
    dlc_model/                         DeepLabCut eye-tracking model (CC BY 4.0)
    protocol/trialsLoop_5dpf.csv       stimulus protocol
    zebrafish_DLC2SMR.ipynb            DeepLabCut coordinates → eye angles
```

## Micro-CT analysis

A segmentation model (EfficientNet-B0 encoder, U-Net decoder) trained on ZEISS arivis Cloud segments the retinal layers and the lens in micro-CT images of the zebrafish eye. All segmentation masks used in the paper were generated with this model in arivis Cloud; a Python notebook is provided for users without access to ZEISS software. A second notebook measures PRL thickness from the masks and plots group-level polar thickness maps. See [`mCT/README.md`](mCT/README.md).

## Optokinetic response analysis

Eye movements were tracked with a DeepLabCut model (Patil et al., 2025), converted to eye angles, and analysed in Spike2. See [`okr/README.md`](okr/README.md).

## Citation

If you use the models or code, please cite the repository.

## Licence

- **Code** (`mCT/inference/`, `mCT/thickness/`, `okr/`): MIT licence, see [`LICENSE`](LICENSE).
- **Segmentation model** (`mCT/models/`): [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/), see [`mCT/models/LICENSE`](mCT/models/LICENSE).
- **DeepLabCut model** (`okr/dlc_model/`): CC BY 4.0, see [`okr/dlc_model/LICENSE`](okr/dlc_model/LICENSE); please cite Patil et al. (2025) and Mathis et al. (2018).

## Contact

[syedmhammad003 github]
