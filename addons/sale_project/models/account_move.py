# -*- coding: utf-8 -*-

from odoo import models


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    def _compute_analytic_account_id(self):
        # when a project creates an aml, it adds an analytic account to it. the following filter is to save this
        # analytic account from being overridden by analytic default rules and lack thereof
        project_amls = self.filtered(lambda aml: aml.analytic_account_id and any(aml.sale_line_ids.project_id))
        super(AccountMoveLine, self - project_amls)._compute_analytic_account_id()
