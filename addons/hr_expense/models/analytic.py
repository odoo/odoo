# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class AccountAnalyticApplicability(models.Model):
    _inherit = 'account.analytic.applicability'
    _description = "Analytic Plan's Applicabilities"

    business_domain = fields.Selection(
        selection_add=[
            ('expense', 'Expense'),
        ],
        ondelete={'expense': 'cascade'},
    )


class AnalyticAccount(models.Model):
    _inherit = 'account.analytic.account'

    @api.ondelete(at_uninstall=False)
    def _unlink_except_account_in_analytic_distribution(self):
        self.env.cr.execute("""
            SELECT id FROM hr_expense
                WHERE analytic_distribution::jsonb ?| array[%s]
            LIMIT 1
        """, ([str(id) for id in self.ids],))
        expense_ids = self.env.cr.fetchall()
        if expense_ids:
            raise UserError(_("You cannot delete an analytic account that is used in an expense."))
