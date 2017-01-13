# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields


class AccountConfigSettings(models.TransientModel):
    _inherit = 'account.config.settings'

    tax_cash_basis_journal_id = fields.Many2one(
        'account.journal',
        related='company_id.tax_cash_basis_journal_id',
        string="Tax Cash Basis Journal",)
