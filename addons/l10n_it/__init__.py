# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from . import models


def load_translations(env):
    env.ref('l10n_it.l10n_it_chart_template_generic').process_coa_translations()
