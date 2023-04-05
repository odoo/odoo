# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from . import models, controllers

def auto_install_l10n(env):
    if not env.company.l10n_installed:
        env.company.country_id.l10n_module_id.button_install()
