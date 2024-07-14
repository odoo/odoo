# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import io
from math import copysign
from odoo import _, models
from odoo.tools.misc import xlsxwriter
from odoo import fields


class AccountGenericTaxReport(models.AbstractModel):
    _name = "l10n_th.tax.report.handler"
    _inherit = "account.generic.tax.report.handler"
    _description = "Thai Tax Report Custom Handler"

    def _custom_options_initializer(self, report, options, previous_options=None):
        super()._custom_options_initializer(report, options, previous_options=previous_options)
        if self.env.company.account_fiscal_country_id.code == 'TH':
            options.setdefault('buttons', []).extend((
                {
                    'name': _('Sales Tax Report (xlsx)'),
                    'action': 'export_file',
                    'action_param': 'l10n_th_print_sale_tax_report',
                    'sequence': 82,
                    'file_export_type': _('Sales Tax Report (xlsx)')
                },
                {
                    'name': _('Purchase Tax Report (xlsx)'),
                    'action': 'export_file',
                    'action_param': 'l10n_th_print_purchase_tax_report',
                    'sequence': 83,
                    'file_export_type': _('Purchase Tax Report (xlsx)')
                }
            ))

    def _dynamic_lines_generator(self, report, options, all_column_groups_expression_totals, warnings=None):
        return []

    def l10n_th_print_sale_tax_report(self, options):
        domain = [('journal_id.type', '=', 'sale'), ('payment_state', '!=', 'reversed'),
                  '|', ('reversed_entry_id.payment_state', '!=', 'reversed'), ('reversed_entry_id', '=', False)]
        data = self._l10n_th_print_tax_report(options, domain, origin_type='sale')
        return {
            "file_name": _("Sales Tax Report"),
            "file_content": data,
            "file_type": "xlsx",
        }

    def l10n_th_print_purchase_tax_report(self, options):
        domain = [('journal_id.type', '=', 'purchase'), ('payment_state', '!=', 'reversed'),
                  '|', ('reversed_entry_id.payment_state', '!=', 'reversed'), ('reversed_entry_id', '=', False)]
        data = self._l10n_th_print_tax_report(options, domain, origin_type='purchase')
        return {
            "file_name": _("Purchase Tax Report"),
            "file_content": data,
            "file_type": "xlsx",
        }

    def _l10n_th_print_tax_report(self, options, domain, origin_type='sale'):
        date_from = options['date'].get('date_from')
        date_to = options['date'].get('date_to')
        domain += [('date', '>=', date_from), ('date', '<=', date_to)]
        if options.get('all_entries'):
            domain += [('state', 'in', ['draft', 'posted'])]
        else:
            domain += [('state', '=', 'posted')]
        moves = self.env['account.move'].search(domain)
        return self._generate_data(moves, origin_type, date_from, date_to)

    def _generate_data(self, moves, origin_type, date_from, date_to):
        file_data = io.BytesIO()
        workbook = xlsxwriter.Workbook(file_data, {
            'in_memory': True,
        })
        sheet = workbook.add_worksheet()

        currency_default_style = workbook.add_format({'font_name': 'Arial', 'font_size': 10, 'num_format': '฿#,##0.00'})
        date_default_style = workbook.add_format({'font_name': 'Arial', 'font_size': 10, 'num_format': 'dd/mm/yyyy'})
        default_style = workbook.add_format({'font_name': 'Arial', 'font_size': 10})
        title_style = workbook.add_format({'font_name': 'Arial', 'font_size': 18, 'bold': True, 'align': 'center'})
        center_style = workbook.add_format({'font_name': 'Arial', 'font_size': 10, 'align': 'center'})
        col_header_style = workbook.add_format(
            {'font_name': 'Arial', 'font_size': 10, 'bold': True, 'bg_color': '#d9d9d9'})

        sheet.set_column(0, 0, 4)
        sheet.set_column(1, 1, 15.2)
        sheet.set_column(2, 2, 11.2)
        sheet.set_column(3, 3, 16)
        sheet.set_column(4, 4, 15.2)
        sheet.set_column(5, 5, 19.2)
        sheet.set_column(6, 7, 14)

        y_offset = 0

        title_dict = {'sale': _('Sales Tax Report'), 'purchase': _('Purchase Tax Report')}
        title = title_dict.get(origin_type, _('Tax Report'))
        sheet.merge_range(y_offset, 0, y_offset, 9, title, title_style)
        y_offset += 1

        date_from = fields.Date.to_date(date_from).strftime('%d/%m/%Y')
        date_to = fields.Date.to_date(date_to).strftime("%d/%m/%Y")
        date = _("From %s to %s", date_from, date_to)
        company = self.env.company
        company_name = company.name
        vat = company.vat or ''

        infos = [date, company_name, vat, company.partner_id.l10n_th_branch_name]
        for info in infos:
            sheet.merge_range(y_offset, 0, y_offset, 9, info, center_style)
            y_offset += 1
        y_offset += 1

        sheet.set_row(y_offset, 32.7)
        headers = [_("No."), _("Tax Invoice No."), _("Reference"), _("Invoice Date"), _("Contact Name"),
                   _("Tax ID"), _("Company Information"), _("Total Amount"), _("Total Excluding VAT Amount"), _("Vat Amount")]
        for index, header in enumerate(headers):
            sheet.write(y_offset, index, header, col_header_style)
        y_offset += 1

        accumulate_total = 0
        accumulate_untaxed_signed = 0
        accumulate_tax = 0

        tax_group_vat_7 = self.env.ref(f'account.{self.env.company.id}_tax_group_vat_7')
        for index, move in enumerate(moves):
            sign = move.reversed_entry_id.payment_state == 'partial' and -1 or 1
            amount_total = sign * copysign(move.amount_total_signed, move.amount_total)
            amount_untaxed_signed = sign * abs(move.amount_untaxed_signed)
            # Only include tax amount from VAT 7% tax group
            amount_tax = 0.0
            for taxes in move.tax_totals['groups_by_subtotal'].values():
                for tax in taxes:
                    if tax['tax_group_id'] == tax_group_vat_7.id:
                        is_company_currency = move.currency_id == company.currency_id
                        amount_tax += sign * (tax['tax_group_amount'] if is_company_currency else tax['tax_group_amount_company_currency'])
            sheet.write(y_offset, 0, index + 1, default_style)
            sheet.write(y_offset, 1, move.name, default_style)
            sheet.write(y_offset, 2, move.ref or '', default_style)
            sheet.write(y_offset, 3, move.date, date_default_style)
            sheet.write(y_offset, 4, move.partner_id.name or '', default_style)
            sheet.write(y_offset, 5, move.partner_id.vat or '', default_style)
            sheet.write(y_offset, 6, move.partner_id.l10n_th_branch_name, default_style)
            sheet.write(y_offset, 7, amount_total, currency_default_style)
            sheet.write(y_offset, 8, amount_untaxed_signed, currency_default_style)
            sheet.write(y_offset, 9, amount_tax, currency_default_style)
            accumulate_total += amount_total
            accumulate_untaxed_signed += amount_untaxed_signed
            accumulate_tax += amount_tax
            y_offset += 1
        y_offset += 1
        y_offset += 1

        sheet.write(y_offset, 6, "Total", default_style)
        sheet.write(y_offset, 7, accumulate_total, currency_default_style)
        sheet.write(y_offset, 8, accumulate_untaxed_signed, currency_default_style)
        sheet.write(y_offset, 9, accumulate_tax, currency_default_style)
        y_offset += 1

        workbook.close()
        file_data.seek(0)
        data = file_data.read()

        return data
