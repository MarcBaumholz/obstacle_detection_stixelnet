#!/usr/bin/env python
# -*- coding: utf-8 -*-
from tensorflow.keras.callbacks import (
    ModelCheckpoint,
    ReduceLROnPlateau,
    EarlyStopping,
)
from tensorflow.keras import optimizers
from albumentations import (
    Resize,
    Compose,
    CLAHE,
    HueSaturationValue,
    RandomBrightness,
    RandomContrast,
    RandomGamma,
    ToFloat,
    Normalize,
    GaussNoise,
    RandomShadow,
    RandomRain,
)
import os
import numpy as np
from config import Config
from data_loader import WaymoStixelDataset
from models import StixelLoss, build_stixel_net
import utility
from tensorflow.keras.utils import OrderedEnqueuer

import argparse

parser = argparse.ArgumentParser()
parser.add_argument("--batch_size", type=int, default=2)#1
parser.add_argument("--num_epoch", type=int, default=50)#11
parser.add_argument("--load_checkpoint", type=str, default='')
parsed_args = parser.parse_args()


def main():
    dt_config = Config()
    dt_config.display()
    starting_ckeckpoint_epoch = 11

    train_aug = Compose(
        [
            GaussNoise(p=1.0),
            RandomShadow(p=0.5),
            RandomRain(p=0.5, rain_type="drizzle"),
            RandomContrast(limit=0.2, p=0.5),
            RandomGamma(gamma_limit=(80, 120), p=0.5),
            RandomBrightness(limit=0.2, p=0.5),
            HueSaturationValue(
                hue_shift_limit=5, sat_shift_limit=20, val_shift_limit=10, p=0.5
            ),
            CLAHE(p=0.5, clip_limit=2.0),
            Normalize(p=1.0),
        ]
    )

    val_aug = Compose([Normalize(p=1.0)])
    train_set = WaymoStixelDataset(
        data_path=dt_config.DATA_PATH,
        ground_truth_path=os.path.join(dt_config.DATA_PATH, "waymo_train.txt"),
        batch_size=parsed_args.batch_size,
        transform=train_aug,
        customized_transform=utility.HorizontalFlip(p=0.5),
    )

    val_set = WaymoStixelDataset(
        data_path=dt_config.DATA_PATH,
        ground_truth_path=os.path.join(dt_config.DATA_PATH, "waymo_val.txt"),
        transform=val_aug,
    )

    model = build_stixel_net()
    loss_func = StixelLoss()
    #opt = optimizers.Adam(0.0001, clipnorm=1) 
    #opt = optimizers.Adam(0.000025, clipnorm=1)
    opt = optimizers.Adam(3e-4, clipnorm=0.1)
    callbacks = [
        ModelCheckpoint(
            os.path.join(dt_config.SAVED_MODELS_PATH, "model-{epoch:03d}-{loss:.4f}.h5"),
            monitor="val_loss",
            verbose=1,
            save_best_only=True,
            mode="auto",
            period=1,
        ),
        ReduceLROnPlateau(
            monitor="val_loss",
            factor=0.1,
            patience=7,
            verbose=0,
            mode="auto",
            min_lr=0.000001,
        ),
        EarlyStopping(
            monitor="val_loss", min_delta=0, patience=10, verbose=0, mode="auto"
        ),
    ]

    model.compile(loss=loss_func, optimizer=opt)
    model.summary()

    if parsed_args.load_checkpoint != '':
        assert os.path.isfile(parsed_args.load_checkpoint)
        model.load_weights(parsed_args.load_checkpoint)

    history = model.fit_generator(
        train_set,
        steps_per_epoch=len(train_set),
        validation_data=val_set,
        validation_steps=len(val_set),
        epochs=parsed_args.num_epoch,
        callbacks=callbacks,
        shuffle=True,
    )

    history_path = os.path.join(dt_config.SAVED_MODELS_PATH, "history.pkl")
    np.save(history_path, history.history)


if __name__ == "__main__":
    main()
