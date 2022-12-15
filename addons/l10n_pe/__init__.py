# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from . import models
from . import demo


def load_translations(env):
    env.ref('l10n_pe.pe_chart_template').process_coa_translations()
