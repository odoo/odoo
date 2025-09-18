"""
Odoo unit testing framework, based on Python unittest.

Some files as case.py, result.py, suite.py are highly modified versions of unittest.
See https://github.com/python/cpython/tree/3.14/Lib/unittest for reference files.
"""

from . import common
from .common import *
from .form import Form, O2MProxy, M2MProxy
