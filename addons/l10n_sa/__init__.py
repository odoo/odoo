# -*- encoding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from . import models


def load_translations(env):
    env.ref('l10n_sa.sa_chart_template_standard').process_coa_translations()
