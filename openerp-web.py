#!/usr/bin/env python
import os,sys

path_root = os.path.dirname(os.path.abspath(__file__))
path_addons = os.path.join(path_root, 'addons')
if path_addons not in sys.path:
    sys.path.insert(0, path_addons)

import base

if __name__ == "__main__":
    base.common.main(sys.argv)
