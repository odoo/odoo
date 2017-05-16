# -*- coding: utf-8 -*-

from odoo import fields, models, _


class AccountConfigSettings(models.TransientModel):
    _inherit = 'account.config.settings'

    module_l10n_be_edi = fields.Boolean(string='E-Invoicing (Belgium)')
