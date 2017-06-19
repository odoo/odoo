# -*- coding: utf-8 -*-

from odoo import fields, models


class AccountConfigSettings(models.TransientModel):
    _inherit = 'account.config.settings'

    module_l10n_mx_edi = fields.Boolean('Mexican Electronic Invoicing')
