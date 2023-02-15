# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from . import models
from . import demo

def load_translations(env):
    env.ref('l10n_ec.l10n_ec_ifrs').process_coa_translations()
