# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

# Copyright (c) 2011 Cubic ERP - Teradata SAC. (http://cubicerp.com).

def load_translations(env):
    env.ref('l10n_pa.l10npa_chart_template').process_coa_translations()
