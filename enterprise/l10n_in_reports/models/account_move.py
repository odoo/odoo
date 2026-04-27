# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import date

from odoo import api, fields, models


class AccountMove(models.Model):
    _inherit = 'account.move'

    l10n_in_transaction_type = fields.Selection(
        selection=[
            ("inter_state", "Inter State"),
            ("intra_state", "Intra State"),
        ],
        string="Indian Transaction Type",
        compute="_compute_l10n_in_transaction_type",
        store=True,
    )

    @api.depends("country_code", "l10n_in_state_id", "company_id")
    def _compute_l10n_in_transaction_type(self):
        self.fetch(['country_code', 'l10n_in_state_id',"company_id"])
        for move in self:
            if move.country_code == "IN":
                if move.l10n_in_state_id and move.l10n_in_state_id == move.company_id.state_id:
                    move.l10n_in_transaction_type = 'intra_state'
                else:
                    move.l10n_in_transaction_type = 'inter_state'
            else:
                move.l10n_in_transaction_type = False

    def get_fiscal_year_start_date(self, company, invoice_date):
        fiscal_year_start_month = (int(company.fiscalyear_last_month) % 12) + 1
        fiscal_year_start_date = date(invoice_date.year, fiscal_year_start_month, 1)
        if invoice_date.month <= 11:
            fiscal_year_start_date = fiscal_year_start_date.replace(year=invoice_date.year - 1)
        return fiscal_year_start_date
