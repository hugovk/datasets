# coding=utf-8
# Copyright 2020 The HuggingFace Datasets Authors and the current dataset script contributor.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Imagewoof dataset."""


import os

import pandas as pd

import datasets
from datasets.tasks import ImageClassification


_CITATION = """\
@misc{imagewoof,
  author    = "Jeremy Howard",
  title     = "imagewoof",
  url       = "https://github.com/fastai/imagenette/"
}
"""

_DESCRIPTION = """\
Imagewoof is a subset of 10 dog breed classes from Imagenet. The breeds are: Australian terrier, Border terrier, Samoyed, Beagle, Shih-Tzu, English foxhound, Rhodesian ridgeback, Dingo, Golden retriever, Old English sheepdog.
"""

_HOMEPAGE = "https://github.com/fastai/imagenette"

_LICENSE = "Unknown"

_BASE_DOWNLOAD_URL = "https://s3.amazonaws.com/fast-ai-imageclas/{}.tgz"

_LABELS = [
    "n02086240",
    "n02087394",
    "n02088364",
    "n02089973",
    "n02093754",
    "n02096294",
    "n02099601",
    "n02105641",
    "n02111889",
    "n02115641",
]

_BASE_CONFIG_NAMES = ["full-size", "full-size-v2", "320px", "320px-v2", "160px", "160px-v2"]
_NOISY_CONFIG_NAMES = [
    f"{name}-noisy-{noise_pct}" for name in _BASE_CONFIG_NAMES if "v2" in name for noise_pct in [1, 5, 25, 50]
]


class ImagewoofConfig(datasets.BuilderConfig):
    """BuilderConfig for Imagewoof dataset."""

    def __init__(self, name, **kwargs):
        assert "description" not in kwargs
        parts = name.split("-")
        size = "full-size" if "full" in parts else parts[0]
        version = " version 2 " if "v2" in parts else ""
        noisy = (
            f" noisy with with {parts[-1]}% of the labels randomly changed to an incorrect label"
            if "noisy" in parts
            else ""
        )
        super().__init__(
            name=name, description=f"{size}{version}variant{noisy}.", version=datasets.Version("1.0.0"), **kwargs
        )

        base = "imagewoof2" if "v2" in name else "imagewoof"
        suffix = {
            "full-size": "",
            "320px": "-320",
            "160px": "-160",
        }[size]
        self.url = _BASE_DOWNLOAD_URL.format(base + suffix)


class Imagewoof(datasets.GeneratorBasedBuilder):
    """Imagewoof dataset."""

    BUILDER_CONFIGS = [ImagewoofConfig(name=name) for name in _BASE_CONFIG_NAMES + _NOISY_CONFIG_NAMES]

    DEFAULT_CONFIG_NAME = "full-size-v2"

    def _info(self):
        features = datasets.Features(
            {
                "image": datasets.Image(),
            }
        )
        if "noisy" in self.config.name:
            features.update(
                {
                    "noisy_label": datasets.ClassLabel(names=_LABELS),
                    "valid_label": datasets.ClassLabel(names=_LABELS),
                }
            )
        else:
            features.update(
                {
                    "label": datasets.ClassLabel(names=_LABELS),
                }
            )
        return datasets.DatasetInfo(
            description=_DESCRIPTION,
            features=features,
            homepage=_HOMEPAGE,
            license=_LICENSE,
            citation=_CITATION,
            task_templates=[
                ImageClassification(
                    image_column="image", label_column="noisy_label" if "noisy" in self.config.name else "label"
                )
            ],
        )

    def _split_generators(self, dl_manager):
        archive = dl_manager.download(self.config.url)
        return [
            datasets.SplitGenerator(
                name=datasets.Split.TRAIN,
                gen_kwargs={
                    "files": dl_manager.iter_archive(archive),
                    "split": "train",
                },
            ),
            datasets.SplitGenerator(
                name=datasets.Split.VALIDATION,
                gen_kwargs={
                    "files": dl_manager.iter_archive(archive),
                    "split": "val",
                },
            ),
        ]

    def _generate_examples(self, files, split):
        if "noisy" in self.config.name:
            label_col = f"noisy_labels_{self.config.name.rsplit('-', 1)[-1]}"
            metadata = None
            for idx, (path, file) in enumerate(files):
                if os.path.basename(path) == "noisy_imagewoof.csv":
                    metadata = pd.read_csv(file)
                    metadata = metadata.set_index("path")
                else:
                    assert metadata is not None
                    row = metadata.loc["/".join(path.replace("\\", "/").split("/")[-3:])]
                    yield idx, {
                        "image": {"path": path, "bytes": file.read()},
                        "noisy_label": row[label_col],
                        "valid_label": row["noisy_labels_0"],
                    }
        else:
            for idx, (path, file) in enumerate(files):
                if split in path and path.endswith(".JPEG"):
                    yield idx, {
                        "image": {"path": path, "bytes": file.read()},
                        "label": os.path.basename(os.path.dirname(path)),
                    }
