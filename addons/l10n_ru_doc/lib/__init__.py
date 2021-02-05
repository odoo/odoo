# -*- coding: utf-8 -*-
import os, sys, inspect
search_folder = os.path.dirname(inspect.getsourcefile(lambda _: None))
if search_folder not in sys.path: sys.path.insert(0, search_folder)
# from pkg_resources import require
# require('pytils')
# import pytils