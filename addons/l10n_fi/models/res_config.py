# coding=utf-8
# Part of Odoo. See LICENSE file for full copyright and licensing details.

# Copyright (C) Avoin.Systems 2016
from openerp import api, fields, models


class FinnishAccountSettings(models.TransientModel):
    _inherit = 'account.config.settings'

    payment_reference_type = fields.Selection(
        related='company_id.payment_reference_type',
        required=True,
    )

    @api.onchange('company_id')
    def onchange_company_id(self):
        # update related fields
        if self.company_id:
            company = self.company_id
            self.payment_reference_type = company.payment_reference_type
