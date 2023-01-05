# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from . import models
from . import demo
from odoo import api, SUPERUSER_ID

def load_translations(cr, registry):
    env = api.Environment(cr, SUPERUSER_ID, {})
    env.ref('l10n_ec.l10n_ec_ifrs').process_coa_translations()
