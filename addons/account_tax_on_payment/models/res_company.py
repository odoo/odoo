# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    account_advance_payment_tax_account_id = fields.Many2one('account.account', string='Advance Payment Tax Account')
    account_advance_payment_tax_adjustment_journal_id = fields.Many2one('account.journal', string='Advance Payment Tax Adjustment Journal')
