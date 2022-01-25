# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from . import models
<<<<<<< HEAD:addons/hr_recruitment_skills/__init__.py
from . import wizard
=======
from odoo import api, SUPERUSER_ID


def _post_init_hook(cr, registry):
    env = api.Environment(cr, SUPERUSER_ID, {})
    modules = env['ir.module.module'].search([('name', '=', 'account_edi_ubl_cii'), ('state', '=', 'uninstalled')])
    modules.sudo().button_install()
>>>>>>> 3f492199955... temp:addons/l10n_nl_edi/__init__.py
