import re


def patch_re():
    re._MAXCACHE = 4096  # default is 512, a little too small for odoo
