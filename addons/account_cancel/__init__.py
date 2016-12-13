# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import models

from odoo.exceptions import ValidationError

from odoo import api, SUPERUSER_ID, _


def _pre_install_account_cancel(cr):
    env = api.Environment(cr, SUPERUSER_ID, {})
    if env['ir.module.module'].search([('name', '=', 'l10n_fr'), ('state', '=', 'installed')]):
        raise ValidationError(_('You cannot install Cancel Journal Entries module. \n To install this module, first you have to uninstall "France - Accounting" module.'))
