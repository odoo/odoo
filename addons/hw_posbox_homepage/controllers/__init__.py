# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from . import jinja
from . import main
from . import technicals    # purposfully load the technicals module before technical
from . import technical     # as the technical menu need to know which technicals modules were loaded
