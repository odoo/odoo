# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, fields, models


class HrExpenseSheet(models.Model):
    _inherit = "hr.expense.sheet"

    @api.model
    def _get_journal_domain(self):
        default_company_id = self.default_get(['company_id'])['company_id']
        if self.env['res.company'].browse(default_company_id).country_id.code == 'CL':
            return [('type', '=', 'general'), ('company_id', '=', default_company_id)]
        return [('type', '=', 'purchase'), ('company_id', '=', default_company_id)]

    @api.model
    def _default_journal_id(self):
        """ The journal is determining the company of the accounting entries generated from expense. We need to
        force journal company and expense sheet company to be the same. """
        journal_domain = self._get_journal_domain()
        journal = self.env['account.journal'].search(journal_domain, limit=1)
        return journal.id

    journal_id = fields.Many2one(
        'account.journal', string='Expense Journal',
        states={'done': [('readonly', True)], 'post': [('readonly', True)]}, check_company=True,
        domain=_get_journal_domain, default=_default_journal_id, help="The journal used when the expense is done.")
