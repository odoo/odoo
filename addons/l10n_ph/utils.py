# Part of Odoo. See LICENSE file for full copyright and licensing details.
import io
import re
from collections import defaultdict

import xlsxwriter
import xlwt

from odoo.tools.misc import format_date

COLUMN_HEADER_MAP = {
    "Reporting_Month": "invoice_date",
    "Vendor_TIN": "vat",
    "branchCode": "branch_code",
    "companyName": "company_name",
    "surName": "last_name",
    "firstName": "first_name",
    "middleName": "middle_name",
    "address": "address",
    "zip_code": "zip",
    "nature": "tax_description",
    "ATC": "atc",
    "income_payment": "price_subtotal",
    "ewt_rate": "amount",
    "tax_amount": "tax_amount",
}


def write_row(self, row, col, data):
    for token in data:
        self.write(row, col, token)
        col += 1


xlwt.Worksheet.write_row = write_row


def _export_bir_2307(sheet_title, moves, file_format='xlsx'):
    output = io.BytesIO()
    if file_format == 'xls':
        workbook = xlwt.Workbook(encoding='utf-8')
        worksheet = workbook.add_sheet(sheet_title)
    else:
        workbook = xlsxwriter.Workbook(output, {
            'in_memory': True,
            'strings_to_formulas': False,  # As we need to give a default value when using formulas, we need to handle them manually so this is not needed.
        })
        worksheet = workbook.add_worksheet(sheet_title)

    worksheet.write_row(0, 0, list(COLUMN_HEADER_MAP.keys()))
    worksheet_row = 1
    for move in moves.sorted(lambda m: (m.invoice_date or m.date, m.name)):
        partner = move.commercial_partner_id
        partner_address_info = [partner.street, partner.street2, partner.city, partner.state_id.name, partner.country_id.name]
        first_name = middle_name = last_name = ''
        if partner.company_type == 'person':
            first_name = partner.first_name or ''
            middle_name = partner.middle_name or ''
            last_name = partner.last_name or ''
        values = {
            'invoice_date': format_date(move.env, move.invoice_date or move.date, date_format="MM/dd/yyyy"),
            'vat': re.sub(r'-', '', partner.vat)[:9] if partner.vat else '',
            'branch_code': partner.branch_code or '000',
            'company_name': partner.name if partner.company_type == 'company' else '',
            'first_name': first_name,
            'middle_name': middle_name,
            'last_name': last_name,
            'address': ', '.join([val for val in partner_address_info if val]),
            'zip': partner.zip or '',
        }
        aggregated_taxes = _prepare_invoice_aggregated_taxes(move)
        for invoice_line, tax_details_for_line in aggregated_taxes['tax_details_per_record'].items():
            for tax, tax_detail in tax_details_for_line['tax_details'].items():
                if not tax.l10n_ph_atc:
                    continue

                values['tax_description'] = tax.description or ''
                values['atc'] = tax.l10n_ph_atc
                values['price_subtotal'] = tax_detail['base_amount']
                values['amount'] = abs(tax.amount)
                values['tax_amount'] = abs(tax_detail['tax_amount'])
                worksheet.write_row(worksheet_row, 0, [values[field] for field in COLUMN_HEADER_MAP.values()])
                worksheet_row += 1

    if file_format == 'xls':
        workbook.save(output)
    else:
        workbook.close()

    output.seek(0)
    return output.read()


def _prepare_invoice_aggregated_taxes(move):
    AccountTax = move.env['account.tax']

    base_amls = move.line_ids.filtered(lambda x: x.display_type == 'product' and x.tax_ids)
    base_lines = [
        {
            **move._prepare_product_base_line_for_taxes_computation(x),
            'calculate_withholding_taxes': True,
        } for x in base_amls
    ]
    tax_amls = move.line_ids.filtered('tax_repartition_line_id')
    tax_lines = [AccountTax._prepare_tax_line_for_taxes_computation(x, sign=move.direction_sign) for x in tax_amls]
    AccountTax._add_tax_details_in_base_lines(base_lines, move.company_id)
    AccountTax._round_base_lines_tax_details(base_lines, move.company_id, tax_lines=tax_lines)

    results = {
        'base_amount_currency': 0.0,
        'base_amount': 0.0,
        'tax_amount_currency': 0.0,
        'tax_amount': 0.0,
        'tax_details_per_record': defaultdict(lambda: {
            'base_amount_currency': 0.0,
            'base_amount': 0.0,
            'tax_amount_currency': 0.0,
            'tax_amount': 0.0,
        }),
        'base_lines': base_lines,
    }

    def total_grouping_function(base_line, tax_data):
        if tax_data:
            return True

    base_lines_aggregated_values = AccountTax._aggregate_base_lines_tax_details(base_lines, total_grouping_function)
    for base_line, aggregated_values in base_lines_aggregated_values:
        record = base_line['record']
        base_line_results = results['tax_details_per_record'][record]
        base_line_results['base_line'] = base_line
        for grouping_key, values in aggregated_values.items():
            if grouping_key:
                for key in ('base_amount', 'base_amount_currency', 'tax_amount', 'tax_amount_currency'):
                    base_line_results[key] += values[key]

    values_per_grouping_key = AccountTax._aggregate_base_lines_aggregated_values(base_lines_aggregated_values)
    for grouping_key, values in values_per_grouping_key.items():
        if grouping_key:
            for key in ('base_amount', 'base_amount_currency', 'tax_amount', 'tax_amount_currency'):
                results[key] += values[key]

    def tax_details_grouping_function(base_line, tax_data):
        if not total_grouping_function(base_line, tax_data):
            return None
        return tax_data['tax']

    base_lines_aggregated_values = AccountTax._aggregate_base_lines_tax_details(base_lines, tax_details_grouping_function)
    for base_line, aggregated_values in base_lines_aggregated_values:
        record = base_line['record']
        base_line_results = results['tax_details_per_record'][record]
        base_line_results['tax_details'] = tax_details = {}
        for grouping_key, values in aggregated_values.items():
            if not grouping_key:
                continue
            if isinstance(grouping_key, dict):
                values.update(grouping_key)
            tax_details[grouping_key] = values

    values_per_grouping_key = AccountTax._aggregate_base_lines_aggregated_values(base_lines_aggregated_values)
    results['tax_details'] = tax_details = {}
    for grouping_key, values in values_per_grouping_key.items():
        if not grouping_key:
            continue
        if isinstance(grouping_key, dict):
            values.update(grouping_key)
        tax_details[grouping_key] = values

    return results
