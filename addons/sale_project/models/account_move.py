# -*- coding: utf-8 -*-

from odoo import models
from odoo.tools.sql import create_index


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    def init(self):
        super().init()
        create_index(self._cr, 'account_move_line_analytic_distribution', self._table, ['analytic_distribution'], 'gin')

    def _compute_analytic_distribution(self):
        # when a project creates an aml, it adds an analytic account to it. the following filter is to save this
        # analytic account from being overridden by analytic default rules and lack thereof
        project_amls = self.filtered(lambda aml: aml.analytic_distribution and any(aml.sale_line_ids.project_id))
        super(AccountMoveLine, self - project_amls)._compute_analytic_distribution()
