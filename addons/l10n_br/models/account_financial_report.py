# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
# Copyright (C) 2017 KMEE INFORMATICA LTDA (https://www.kmee.com.br)

from __future__ import division, print_function, unicode_literals

from odoo import api, fields, models
from ..constantes import (
    REPORT_TYPE_ADD,
    REPORT_TYPE_VIEW
)


class AccountFinancialReport(models.Model):
    _inherit = 'account.financial.report'
    # _parent_name = 'parent_id'
    # _parent_store = True
    # _parent_order = 'sequence, name'
    _order = 'parent_id, sequence'

    is_brazilian_financial_report = fields.Boolean(
        string='Is Brazilian Financial Report?',
    )
    summary_report_ids = fields.Many2many(
        comodel_name='account.financial.report',
        relation='account_financial_report_self',
        column1='report_id',
        column2='summary_report_id',
        string='Summarized Report',
    )
    type = fields.Selection(
        selection_add=REPORT_TYPE_ADD,
        default=REPORT_TYPE_VIEW,
    )
    redutor = fields.Boolean(
        string='Redutor?',
        compute='_compute_redutor',
        store=True,
    )

    @api.depends('name')
    def _compute_redutor(self):
        for report in self:
            if report.name and (report.name.startswith('(-)')
                                or report.name.startswith('( - )')):
                report.redutor = True
            else:
                report.redutor = False
