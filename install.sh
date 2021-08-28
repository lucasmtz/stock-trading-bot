#!/bin/bash
conda update -y -n base -c defaults conda
conda create -y --prefix ./env python=3.9
conda activate ./env
pip install -r requirements.txt