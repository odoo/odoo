# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields


class ResCompany(models.Model):
    _inherit = 'res.company'

    tax_cash_basis_journal_id = fields.Many2one('account.journal', string="Tax Cash Basis Journal")
