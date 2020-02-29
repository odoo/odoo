# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class AccountInvoiceReport(models.Model):
    _inherit = 'account.invoice.report'

    team_id = fields.Many2one('crm.team', string='Sales Team')

    def _select(self):
        return super(AccountInvoiceReport, self)._select() + ", move.team_id as team_id"

    def _group_by(self):
        return super(AccountInvoiceReport, self)._group_by() + ", move.team_id"
