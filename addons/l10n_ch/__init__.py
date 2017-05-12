# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

# Author: Nicolas Bessi. Copyright Camptocamp SA
# Financial contributors: Hasa SA, Open Net SA,
#                         Prisme Solutions Informatique SA, Quod SA
# Translation contributors: brain-tec AG, Agile Business Group

from odoo import api, SUPERUSER_ID

def load_translations(cr, registry):
    env = api.Environment(cr, SUPERUSER_ID, {})
    env.ref('l10n_ch.l10nch_chart_template').process_coa_translations()
