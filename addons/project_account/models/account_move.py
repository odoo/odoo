# -*- coding: utf-8 -*-

from odoo import models


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    def _compute_analytic_account_id(self):
        filtered_set = self.filtered(lambda aml: not (aml.analytic_account_id and any(aml.sale_line_ids.project_id)))
        super(AccountMoveLine, filtered_set)._compute_analytic_account_id()
