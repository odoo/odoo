# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

# Copyright (C) 2016 Onestein (<http://www.onestein.eu>).

from . import models

def load_translations(env):
    env.ref('l10n_nl.l10nnl_chart_template').process_coa_translations()
