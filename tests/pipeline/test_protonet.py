import os
from pathlib import Path

import pytest
import pytorch_lightning as pl
import torch
from torchvision import transforms
from torchvision.models import *
from yacs.config import CfgNode as CN

from kale.embed.image_cnn import *
from kale.loaddata.n_way_k_shot import NWayKShotDataset
from kale.pipeline.protonet import ProtoNetTrainer
from kale.utils.download import download_file_by_url

root_dir = os.path.dirname(os.path.dirname(os.getcwd()))
url = "https://github.com/pykale/data/raw/main/images/omniglot/demo_data.zip"
modes = ["train", "val", "test"]


@pytest.fixture(scope="module")
def testing_cfg_data(download_path):
    cfg = CN()
    cfg.DATASET = CN()
    cfg.DATASET.ROOT = os.path.join(root_dir, download_path, "demo_data")
    yield cfg


@pytest.fixture(scope="module")
def testing_cfg_model():
    _C = CN()
    _C.SEED = 1397
    _C.DEVICE = "cuda"

    _C.MODEL = CN()
    _C.MODEL.BACKBONE = "resnet18"
    _C.MODEL.PRETRAIN_WEIGHTS = None

    _C.TRAIN = CN()
    _C.TRAIN.EPOCHS = 1
    _C.TRAIN.OPTIMIZER = "SGD"
    _C.TRAIN.LEARNING_RATE = 1e-3
    _C.TRAIN.N_WAYS = 30
    _C.TRAIN.K_SHOTS = 5
    _C.TRAIN.K_QUERIES = 15

    _C.VAL = CN()
    _C.VAL.N_WAYS = 5
    _C.VAL.K_SHOTS = 5
    _C.VAL.K_QUERIES = 15

    _C.OUTPUT = CN()
    _C.OUTPUT.LOG_DIR = "logs"
    _C.OUTPUT.WEIGHT_DIR = "weights"
    _C.OUTPUT.SAVE_FREQ = 1
    _C.OUTPUT.SAVE_TOP_K = 2
    _C.OUTPUT.SAVE_LAST = True
    yield _C.clone()


@pytest.mark.parametrize("mode", modes)
def test_protonet(mode, testing_cfg_data, testing_cfg_model):
    cfg_data = testing_cfg_data

    output_dir = str(Path(cfg_data.DATASET.ROOT).parent.absolute())
    download_file_by_url(url=url, output_directory=output_dir, output_file_name="demo_data.zip", file_format="zip")

    cfg_model = testing_cfg_model
    transform = transforms.Compose([transforms.Resize((224, 224)), transforms.ToTensor()])
    dataset = NWayKShotDataset(
        path=cfg_data.DATASET.ROOT,
        mode=mode,
        k_shot=cfg_model.TRAIN.K_SHOTS,
        query_samples=cfg_model.TRAIN.K_QUERIES,
        transform=transform,
    )
    dataloader = torch.utils.data.DataLoader(
        dataset, batch_size=cfg_model.TRAIN.N_WAYS, shuffle=True, num_workers=30, drop_last=True
    )
    net = eval(f"{cfg_model.MODEL.BACKBONE}(weights={cfg_model.MODEL.PRETRAIN_WEIGHTS})")
    if cfg_model.MODEL.BACKBONE.startswith("resnet"):
        net.fc = Flatten()
    model = ProtoNetTrainer(cfg=cfg_model, net=net)
    trainer = pl.Trainer(
        gpus=0, max_epochs=cfg_model.TRAIN.EPOCHS, accelerator="cuda" if torch.cuda.is_available() else "cpu"
    )
    if mode == "train":
        trainer.fit(model, train_dataloaders=dataloader, val_dataloaders=dataloader)
    else:
        trainer.test(model, dataloaders=dataloader)
