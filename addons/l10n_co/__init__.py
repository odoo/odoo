# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

# Copyright (C) David Arnold (devCO).
# Author        David Arnold (devCO), dar@devco.co
# Co-Authors    Juan Pablo Aries (devCO), jpa@devco.co
#               Hector Ivan Valencia Muñoz (TIX SAS)
#               Nhomar Hernandez (Vauxoo)
#               Humberto Ochoa (Vauxoo)

from . import models

def load_translations(env):
    env.ref('l10n_co.l10n_co_chart_template_generic').process_coa_translations()
