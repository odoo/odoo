# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, api


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    company_country_id = fields.Many2one(
        'res.country', string="Company country", readonly=True,
        related='company_id.account_fiscal_country_id'
    )
    intrastat_default_invoice_transaction_code_id = fields.Many2one(
        'account.intrastat.code',
        string='Default invoice transaction code',
        related='company_id.intrastat_default_invoice_transaction_code_id',
        readonly=False,
    )
    intrastat_default_refund_transaction_code_id = fields.Many2one(
        'account.intrastat.code',
        string='Default refund transaction code',
        related='company_id.intrastat_default_refund_transaction_code_id',
        readonly=False,
    )
