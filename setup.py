#!/usr/bin/env python

import os
from distutils.core import setup

folder = os.path.dirname(os.path.realpath(__file__))
requirements_path = os.path.join(folder, 'requirements.txt')
install_requires = []
if os.path.isfile(requirements_path):
    with open(requirements_path) as f:
        install_requires = f.read().splitlines()

setup(name='wv_gtsam',
      version='0.1',
      description='Installation of GTSAM and basic usage',
      author='WareVision LLC Team',
      author_email='',
      package_dir={},
      packages=["wv_gtsam", "wv_gtsam.dataset", "wv_gtsam.dataset.structures", "wv_gtsam.barcode_detector",
                "wv_gtsam.barcode_detector.utils"],
      install_requires=install_requires
      )
