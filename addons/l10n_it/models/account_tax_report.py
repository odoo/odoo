# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, _


class AccountTaxReportLine(models.AbstractModel):
    _inherit = "account.tax.report.line"

    carry_over_condition_method = fields.Selection(
        selection_add=[
            ('vp14_debt_carryover_condition', 'Italian line vp14 debt carryover'),
            ('vp14_credit_carryover_condition', 'Italian line vp14 credit carryover'),
        ]
    )

    def vp14_debt_carryover_condition(self, options, line_amount, carried_over_amount):
        """
        The vp14 debt line will be carried over to the vp7 line of the next period, if the amount is between 0 and 25.82
        Else the amount in vp7 will stay 0
        """
        if options['tax_unit'] == 'company_only':
            company = self.env.company
        else:
            tax_unit = self.env['account.tax.unit'].browse(options['tax_unit'])
            company = tax_unit.main_company_id

        base_currency = company.currency_id
        target_currency = self.env.ref('base.EUR')

        amount_in_euro = base_currency._convert(line_amount, target_currency, company, options['date']['date_to'])
        if amount_in_euro <= 25.82:
            return (None, 0)
        else:
            return (None, None)

    def vp14_credit_carryover_condition(self, options, line_amount, carried_over_amount):
        """
        If there is a credit, this amount will be carried over to the vp8 line of the next period.
        This is only done during the same year.
        If we are between two years, we want to carry it over to the vp9 line.
        """
        return (None, 0)

    def _get_carryover_destination_line(self, options):
        self.ensure_one()
        italian_report_id = self.env['ir.model.data']._xmlid_to_res_id('l10n_it.tax_report_vat')
        if self.report_id.id != italian_report_id or self.code != 'VP14b':
            return super()._get_carryover_destination_line(options)

        end_of_period_month = fields.Date.from_string(options['date']['date_to']).month

        # For the line 14, we are having a different target between periods or years
        if end_of_period_month == 12:
            # Between two years, we carryover to the line VP9
            line = self.env.ref('l10n_it.tax_report_line_vp9')
        else:
            line = self.carry_over_destination_line_id or self

        return line
