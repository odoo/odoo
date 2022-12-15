# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

# Copyright (C) 2010 Savoir-faire Linux (<https://www.savoirfairelinux.com>).

from . import models


def load_translations(env):
    env.ref('l10n_ca.ca_en_chart_template_en').process_coa_translations()
