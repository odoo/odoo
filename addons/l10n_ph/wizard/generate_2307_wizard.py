# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64
import io
import re
import xlwt

from odoo import fields, models
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

class Generate2307Wizard(models.TransientModel):
    _name = "l10n_ph_2307.wizard"
    _description = "Exports 2307 data to a XLS file."

    moves_to_export = fields.Many2many("account.move", string="Joural To Include")
    generate_xls_file = fields.Binary(
        "Generated file",
        help="Technical field used to temporarily hold the generated XLS file before its downloaded."
    )

    def _write_single_row(self, worksheet, worksheet_row, values):
        for index, field in enumerate(COLUMN_HEADER_MAP.values()):
            worksheet.write(worksheet_row, index, label=values[field])

    def _write_rows(self, worksheet, moves):
        worksheet_row = 0
        for move in moves:
            worksheet_row += 1
            partner = move.commercial_partner_id
            partner_address_info = [partner.street, partner.street2, partner.city, partner.state_id.name, partner.country_id.name]
            first_name = middle_name = last_name = ''
            if partner.company_type == 'person':
                first_name = partner.first_name or ''
                middle_name = partner.middle_name or ''
                last_name = partner.last_name or ''
            values = {
                'invoice_date': format_date(self.env, move.invoice_date, date_format="MM/dd/yyyy"),
                'vat': re.sub(r'\-', '', partner.vat)[:9] if partner.vat else '',
                'branch_code': partner.branch_code or '000',
                'company_name': partner.name if partner.company_type == 'company' else '',
                'first_name': first_name,
                'middle_name': middle_name,
                'last_name': last_name,
                'address': ', '.join([val for val in partner_address_info if val]),
                'zip': partner.zip or '',
            }
            aggregated_taxes = move._prepare_invoice_aggregated_taxes()
            for invoice_line, tax_details_for_line in aggregated_taxes['tax_details_per_record'].items():
                for tax_detail in tax_details_for_line['tax_details'].values():
                    tax = tax_detail['tax']
                    if not tax.l10n_ph_atc:
                        continue
                    values['tax_description'] = tax.description or ''
                    values['atc'] = tax.l10n_ph_atc
                    values['price_subtotal'] = tax_detail['base_amount']
                    values['amount'] = tax.amount
                    values['tax_amount'] = tax_detail['tax_amount']
                    self._write_single_row(worksheet, worksheet_row, values)
                    worksheet_row += 1

    def action_generate(self):
        """ Generate a xls format file for importing to
        https://bir-excel-uploader.com/excel-file-to-bir-dat-format/#bir-form-2307-settings.
        This website will then generate a BIR 2307 format excel file for uploading to the
        PH government.
        """
        self.ensure_one()

        file_data = io.BytesIO()
        workbook = xlwt.Workbook(encoding='utf-8')
        worksheet = workbook.add_sheet('Form2307')

        for index, col_header in enumerate(COLUMN_HEADER_MAP.keys()):
            worksheet.write(0, index, label=col_header)

        self._write_rows(worksheet, self.moves_to_export)

        workbook.save(file_data)
        file_data.seek(0)
        self.generate_xls_file = base64.b64encode(file_data.read())

        return {
            "type": "ir.actions.act_url",
            "target": "self",
            "url": "/web/content?model=l10n_ph_2307.wizard&download=true&field=generate_xls_file&filename=Form_2307.xls&id={}".format(self.id),
        }
