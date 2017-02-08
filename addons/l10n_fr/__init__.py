# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

# Copyright (c) 2008 JAILLET Simon - CrysaLEAD - www.crysalead.fr

import models

from odoo.exceptions import ValidationError

from odoo import api, SUPERUSER_ID, _


def _pre_install_l10n_fr(cr):
    env = api.Environment(cr, SUPERUSER_ID, {})
    if env['ir.module.module'].search([('name', '=', 'account_cancel'), ('state', '=', 'installed')]):
        raise ValidationError(_('You cannot install France - Accounting module. \n To install this module, first you have to uninstall "Cancel Journal Entries" module.'))
