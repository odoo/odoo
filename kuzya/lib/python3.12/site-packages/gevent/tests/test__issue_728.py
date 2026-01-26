#!/usr/bin/env python
from gevent.monkey import patch_all
patch_all()


if __name__ == '__main__':
    # Reproducing #728 requires a series of nested
    # imports
    __import__('_imports_imports_at_top_level')
