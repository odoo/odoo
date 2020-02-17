# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

# Copyright (C) 2007-2014 Jeff Wang(<http://jeff@osbzr.com>).

from . import models

from odoo import api, SUPERUSER_ID

def load_translations(cr, registry):
    env = api.Environment(cr, SUPERUSER_ID, {})
    env.ref('l10n_cn.l10n_chart_china_small_business').process_coa_translations()
