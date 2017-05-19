# -*- coding: utf-8 -*-

from odoo import fields, models


class AccountConfigSettings(models.TransientModel):
    _inherit = 'account.config.settings'

    vat_check_vies = fields.Boolean(related='company_id.vat_check_vies',
        string='VIES VAT Check')
