# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

# Copyright (C) 2009  Renato Lima - Akretion

from . import models

def load_translations(env):
    env.ref("l10n_br.l10n_br_account_chart_template").process_coa_translations()
