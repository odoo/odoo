"""
Odoo unit testing framework, based on Python unittest.

Some files as case.py, resut.py, suite.py are higly modified versions of unitest
See https://github.com/python/cpython/tree/3.10/Lib/unittest for reference files.
"""

from . import common
from .common import *
from .form import Form, O2MProxy, M2MProxy
from . import test_parse_inline_template
