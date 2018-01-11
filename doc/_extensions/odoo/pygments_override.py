# -*- coding: utf-8 -*-
from pygments.style import Style
from pygments.styles.paraiso_dark import ParaisoDarkStyle
from pygments.token import *

# extracted from getbootstrap.com
class OdooStyle(Style):
    background_color = '#272727'
    highlight_color = ParaisoDarkStyle.highlight_color

    styles = dict(ParaisoDarkStyle.styles)
    styles[Keyword] = '#cb49a8'
    styles[Name.Tag] = '#21b799'

import imp
import sys
modname = 'pygments.styles.odoo'
m = imp.new_module(modname)
m.OdooStyle = OdooStyle
sys.modules[modname] = m
