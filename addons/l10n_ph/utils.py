# Part of Odoo. See LICENSE file for full copyright and licensing details.
import io
import re
import xlwt
import xlsxwriter

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
    "nature": "product_name",
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
    for move in moves:
        partner = move.partner_id
        partner_address_info = [partner.street, partner.street2, partner.city, partner.state_id.name, partner.country_id.name]
        values = {
            'invoice_date': format_date(move.env, move.invoice_date, date_format="MM/dd/yyyy"),
            'vat': re.sub(r'-', '', partner.vat)[:9] if partner.vat else '',
            'branch_code': partner.branch_code or '000',
            'company_name': partner.commercial_partner_id.name,
            'first_name': partner.first_name or '',
            'middle_name': partner.middle_name or '',
            'last_name': partner.last_name or '',
            'address': ', '.join([val for val in partner_address_info if val])
        }
        aggregated_taxes = move._prepare_invoice_aggregated_taxes()
        for invoice_line, tax_details_for_line in aggregated_taxes['tax_details_per_record'].items():
            for tax, tax_detail in tax_details_for_line['tax_details'].items():
                if not tax.l10n_ph_atc:
                    continue

                product_name = invoice_line.product_id.name or invoice_line.name
                values['product_name'] = re.sub(r'[()]', '', product_name) if product_name else ""
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
