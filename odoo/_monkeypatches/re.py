import re

from odoo._monkeypatches import register


def patch_re():
    """ Default is 512, a little too small for odoo """
    re._MAXCACHE = 4096
    register({'re': re})
