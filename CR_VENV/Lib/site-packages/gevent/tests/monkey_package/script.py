# -*- coding: utf-8 -*-
"""
Test script file, to be used directly as a file.
"""
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function


# We need some global imports
from textwrap import dedent

def use_import():
    return dedent("    text")

if __name__ == '__main__':
    import os.path
    print(os.path.abspath(__file__))
    print(__name__)
    print(use_import())
