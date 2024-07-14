# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import io
from datetime import datetime

from odoo import Command, fields, models
from odoo.tools.misc import xlsxwriter

class L10nInGSTReturnPeriod(models.Model):

    _inherit = "l10n_in.gst.return.period"

    gstr1_spreadsheet = fields.Many2one('documents.document')

    def action_open_gstr1_spreadsheet(self):
        return {
            'type': "ir.actions.client",
            'tag': "action_open_spreadsheet",
            'params': {
                'spreadsheet_id': self.gstr1_spreadsheet.id,
            }
        }

    def _get_gstr1_cell_formats(self, workbook):
        return {
            'primary_header': workbook.add_format({'bold': True, 'bg_color': '#0070C0', 'color': '#FFFFFF', 'font_size': 8, 'border': 1, 'align': 'center'}),
            'secondary_header': workbook.add_format({'bg_color': '#F8CBAD', 'font_size': 8, 'align': 'center'}),
            'regular': workbook.add_format({'font_size': 8}),
            'date': workbook.add_format({'font_size': 8, 'num_format': 'dd-mm-yy'}),
            'number': workbook.add_format({'font_size': 8, 'num_format': '0.00'}),
        }

    def generate_gstr1_spreadsheet(self):
        gstr1_json = self._get_gstr1_json()
        if self.gstr1_spreadsheet:
            # archive the old file
            self.gstr1_spreadsheet.active = False
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        cell_formats = self._get_gstr1_cell_formats(workbook)
        self._prepare_b2b_sheet(gstr1_json.get('b2b', {}), workbook, cell_formats)
        self._prepare_b2cl_sheet(gstr1_json.get('b2cl', {}), workbook, cell_formats)
        self._prepare_b2cs_sheet(gstr1_json.get('b2cs', {}), workbook, cell_formats)
        self._prepare_cdnr_sheet(gstr1_json.get('cdnr', {}), workbook, cell_formats)
        self._prepare_cdnur_sheet(gstr1_json.get('cdnur', {}), workbook, cell_formats)
        self._prepare_exp_sheet(gstr1_json.get('exp', {}), workbook, cell_formats)
        self._prepare_nil_sheet(gstr1_json.get('nil', {}), workbook, cell_formats)
        self._prepare_hsn_sheet(gstr1_json.get('hsn', {}), workbook, cell_formats)
        workbook.close()
        xlsx_data = output.getvalue()
        xlsx_doc = self.env['documents.document'].create({
            'name': 'gstr1_%s_monthly_report.xlsx' % self.return_period_month_year,
            'raw': xlsx_data,
            'folder_id': self._get_gstr_document_folder().id,
            'mimetype': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        })
        self.gstr1_spreadsheet = xlsx_doc.clone_xlsx_into_spreadsheet(archive_source=True)
        return self.action_open_gstr1_spreadsheet()

    def _get_gstr_document_folder(self):
        xml_id = 'l10n_in_reports_gstr_spreadsheet.%s_gstr_folder' % self.company_id.id
        gstr_folder = self.env.ref(xml_id, raise_if_not_found=False)
        if not gstr_folder:
            gstr_folder = self.env['documents.folder'].create({
                'name': 'GSTR',
                'company_id': self.company_id.id,
                'group_ids': [Command.link(self.env.ref('account.group_account_manager').id)],
                'read_group_ids': [Command.link(self.env.ref('account.group_account_manager').id)],
            })
            self.env['ir.model.data']._update_xmlids([{
                'xml_id': xml_id,
                'record': gstr_folder,
                'noupdate': True,
            }])
        return gstr_folder

    def _set_spreadsheet_row(self, spreadsheet_data, row_data, cell_row, cell_format=None):
        row_data = (isinstance(row_data, dict) and row_data.values()) or row_data
        for cell in row_data:
            spreadsheet_data.write("%s%s" % (cell['column'], cell_row), cell['val'], cell.get('format') or cell_format)

    def _prepare_b2b_sheet(self, b2b_json, workbook, cell_formats):
        primary_header_row = 2
        secondary_header_row = 4
        totals_val_row = 3
        row_count = 5
        worksheet = workbook.add_worksheet('b2b')
        worksheet.write('A1', 'Summary For B2B,    SEZ,    DE (4A,    4B,    6B,    6C)', cell_formats.get('primary_header'))
        primary_headers = [
           {'val': 'No. of Recipients', 'column': 'A'},
           {'val': 'No. of Invoices', 'column': 'B'},
           {'val': 'Total Invoice Value', 'column': 'D'},
           {'val': 'Total Taxable Value', 'column': 'I'},
           {'val': 'Total Cess', 'column': 'J'},
        ]
        secondary_headers = [
            {'val': 'GSTIN/UIN of Recipient', 'column': 'A'},
            {'val': 'Invoice Number', 'column': 'B'},
            {'val': 'Invoice Date', 'column': 'C'},
            {'val': 'Invoice Value', 'column': 'D'},
            {'val': 'Place Of Supply', 'column': 'E'},
            {'val': 'Reverse Charge', 'column': 'F'},
            {'val': 'Invoice Type', 'column': 'G'},
            {'val': 'Rate', 'column': 'H'},
            {'val': 'Taxable Value', 'column': 'I'},
            {'val': 'Cess Amount', 'column': 'J'},
        ]
        totals_row_data = {
            'total_receiptients': {'val': 0, 'column': 'A'},
            'total_invoices': {'val': 0, 'column': 'B'},
            'total_invoices_val': {'val': 0, 'column': 'D', 'format': cell_formats.get('number')},
            'total_taxable_val': {'val': 0, 'column': 'I', 'format': cell_formats.get('number')},
            'total_cess': {'val': 0, 'column': 'J', 'format': cell_formats.get('number')}
        }
        self._set_spreadsheet_row(worksheet, primary_headers, primary_header_row)
        self._set_spreadsheet_row(worksheet, secondary_headers, secondary_header_row)
        worksheet.set_row(primary_header_row - 1, None, cell_formats.get('primary_header'))
        worksheet.set_row(secondary_header_row - 1, None, cell_formats.get('secondary_header'))
        worksheet.set_column('A:A', 45)
        worksheet.set_column('B:J', 15)
        for gstin_invs in b2b_json:
            totals_row_data['total_receiptients']['val'] += 1
            for inv in gstin_invs.get('inv', {}):
                totals_row_data['total_invoices_val']['val'] += inv['val']
                totals_row_data['total_invoices']['val'] += 1
                for item in inv.get('itms', {}):
                    row_data = [
                        {'val': gstin_invs['ctin'], 'column': 'A'},
                        {'val': inv['inum'], 'column': 'B'},
                        {'val': datetime.strptime(inv['idt'], '%d-%m-%Y'), 'column': 'C', 'format': cell_formats.get('date')},
                        {'val': inv['val'], 'column': 'D', 'format': cell_formats.get('number')},
                        {'val': inv['pos'], 'column': 'E'},
                        {'val': inv['rchrg'], 'column': 'F'},
                        {'val': inv['inv_typ'], 'column': 'G'},
                        {'val': item['itm_det']['rt'], 'column': 'H', 'format': cell_formats.get('number')},
                        {'val': item['itm_det']['txval'], 'column': 'I', 'format': cell_formats.get('number')},
                        {'val': item['itm_det']['csamt'], 'column': 'J', 'format': cell_formats.get('number')},
                    ]
                    self._set_spreadsheet_row(worksheet, row_data, row_count, cell_formats.get('regular'))
                    totals_row_data['total_cess']['val'] += item['itm_det']['csamt']
                    totals_row_data['total_taxable_val']['val'] += item['itm_det']['txval']
                    row_count += 1
        self._set_spreadsheet_row(worksheet, totals_row_data, totals_val_row, cell_formats.get('regular'))

    def _prepare_b2cl_sheet(self, b2cl_json, workbook, cell_formats):
        primary_header_row = 2
        secondary_header_row = 4
        totals_val_row = 3
        row_count = 5
        worksheet = workbook.add_worksheet('b2cl')
        worksheet.write('A1', 'Summary For B2CL(5)', cell_formats.get('primary_header'))
        primary_headers = [
           {'val': 'No. of Invoices', 'column': 'A'},
           {'val': 'Total Invoice Value', 'column': 'C'},
           {'val': 'Total Taxable Value', 'column': 'F'},
        ]
        secondary_headers = [
            {'val': 'Invoice Number', 'column': 'A'},
            {'val': 'Invoice Date', 'column': 'B'},
            {'val': 'Invoice Value', 'column': 'C'},
            {'val': 'Place Of Supply', 'column': 'D'},
            {'val': 'Rate', 'column': 'E'},
            {'val': 'Taxable Value', 'column': 'F'},
            {'val': 'Cess Amount', 'column': 'G'},
        ]
        totals_row_data = {
            'total_invoices': {'val': 0, 'column': 'A'},
            'total_invoices_val': {'val': 0, 'column': 'C', 'format': cell_formats.get('number')},
            'total_taxable_val': {'val': 0, 'column': 'F', 'format': cell_formats.get('number')}
        }
        self._set_spreadsheet_row(worksheet, primary_headers, primary_header_row)
        self._set_spreadsheet_row(worksheet, secondary_headers, secondary_header_row)
        worksheet.set_row(primary_header_row - 1, None, cell_formats.get('primary_header'))
        worksheet.set_row(secondary_header_row - 1, None, cell_formats.get('secondary_header'))
        worksheet.set_column('A:A', 30)
        worksheet.set_column('B:J', 15)
        for b2cl in b2cl_json:
            for inv in b2cl.get('inv', {}):
                totals_row_data['total_invoices_val']['val'] += inv['val']
                totals_row_data['total_invoices']['val'] += 1
                for item in inv.get('itms', {}):
                    row_data = [
                        {'val': inv['inum'], 'column': 'A'},
                        {'val': datetime.strptime(inv['idt'], '%d-%m-%Y'), 'column': 'B', 'format': cell_formats.get('date')},
                        {'val': inv['val'], 'column': 'C', 'format': cell_formats.get('number')},
                        {'val': b2cl['pos'], 'column': 'D'},
                        {'val': item['itm_det']['rt'], 'column': 'E', 'format': cell_formats.get('number')},
                        {'val': item['itm_det']['txval'], 'column': 'F', 'format': cell_formats.get('number')},
                        {'val': item['itm_det']['csamt'], 'column': 'G', 'format': cell_formats.get('number')},
                    ]
                    self._set_spreadsheet_row(worksheet, row_data, row_count, cell_formats.get('regular'))
                    totals_row_data['total_taxable_val']['val'] += item['itm_det']['txval']
                    row_count += 1
        self._set_spreadsheet_row(worksheet, totals_row_data, totals_val_row, cell_formats.get('regular'))

    def _prepare_b2cs_sheet(self, b2cs_json, workbook, cell_formats):
        primary_header_row = 2
        secondary_header_row = 4
        totals_val_row = 3
        row_count = 5
        worksheet = workbook.add_worksheet('b2cs')
        worksheet.write('A1', 'Summary For B2CS(7)', cell_formats.get('primary_header'))
        primary_headers = [
            {'val': 'Total Taxable Value', 'column': 'D'},
            {'val': 'Total Cess', 'column': 'E'},
        ]
        secondary_headers = [
            {'val': '   Type', 'column': 'A'},
            {'val': 'Place Of Supply', 'column': 'B'},
            {'val': 'Rate', 'column': 'C'},
            {'val': 'Taxable Value', 'column': 'D'},
            {'val': 'Cess Amount', 'column': 'E'},
        ]
        totals_row_data = {
        'total_cess': {'val': 0, 'column': 'E', 'format': cell_formats.get('number')},
        'total_taxable_val': {'val': 0, 'column': 'D', 'format': cell_formats.get('number')},
        }
        self._set_spreadsheet_row(worksheet, primary_headers, primary_header_row)
        self._set_spreadsheet_row(worksheet, secondary_headers, secondary_header_row)
        worksheet.set_row(primary_header_row - 1, None, cell_formats.get('primary_header'))
        worksheet.set_row(secondary_header_row - 1, None, cell_formats.get('secondary_header'))
        worksheet.set_column('A:A', 30)
        worksheet.set_column('B:J', 15)
        for b2cs in b2cs_json:
            row_data = [
                {'val': b2cs['typ'], 'column': 'A'},
                {'val': b2cs['pos'], 'column': 'B'},
                {'val': b2cs['rt'], 'column': 'C', 'format': cell_formats.get('number')},
                {'val': b2cs['txval'], 'column': 'D', 'format': cell_formats.get('number')},
                {'val': b2cs['csamt'], 'column': 'E', 'format': cell_formats.get('number')},
            ]
            self._set_spreadsheet_row(worksheet, row_data, row_count, cell_formats.get('regular'))
            totals_row_data['total_taxable_val']['val'] += b2cs['txval']
            totals_row_data['total_cess']['val'] += b2cs['csamt']
            row_count += 1
        self._set_spreadsheet_row(worksheet, totals_row_data, totals_val_row, cell_formats.get('regular'))

    def _prepare_cdnr_sheet(self, cdnr_json, workbook, cell_formats):
        primary_header_row = 2
        secondary_header_row = 4
        totals_val_row = 3
        row_count = 5
        worksheet = workbook.add_worksheet('cdnr')
        worksheet.write('A1', 'Summary For CDNR(9B)', cell_formats.get('primary_header'))
        primary_headers = [
           {'val': 'No. of Recipients', 'column': 'A'},
           {'val': 'No. of Notes', 'column': 'B'},
           {'val': 'Total Note Value', 'column': 'G'},
           {'val': 'Total Taxable Value', 'column': 'I'},
           {'val': 'Total Cess', 'column': 'J'},
        ]
        secondary_headers = [
            {'val': 'GSTIN/UIN of Recipient', 'column': 'A'},
            {'val': 'Note Number', 'column': 'B'},
            {'val': 'Note Date', 'column': 'C'},
            {'val': 'Note Type', 'column': 'D'},
            {'val': 'Place Of Supply', 'column': 'E'},
            {'val': 'Reverse Charge', 'column': 'F'},
            {'val': 'Note Value', 'column': 'G'},
            {'val': 'Rate', 'column': 'H'},
            {'val': 'Taxable Value', 'column': 'I'},
            {'val': 'Cess Amount', 'column': 'J'},
        ]
        totals_row_data = {
            'total_receiptients': {'val':0, 'column': 'A'},
            'total_invoices': {'val':0, 'column': 'B'},
            'total_invoices_val': {'val':0, 'column': 'G', 'format': cell_formats.get('number')},
            'total_taxable_val': {'val':0, 'column': 'I', 'format': cell_formats.get('number')},
            'total_cess': {'val':0, 'column': 'J', 'format': cell_formats.get('number')},
        }
        self._set_spreadsheet_row(worksheet, primary_headers, primary_header_row)
        self._set_spreadsheet_row(worksheet, secondary_headers, secondary_header_row)
        worksheet.set_row(primary_header_row - 1, None, cell_formats.get('primary_header'))
        worksheet.set_row(secondary_header_row - 1, None, cell_formats.get('secondary_header'))
        worksheet.set_column('A:A', 30)
        worksheet.set_column('B:J', 15)
        for gstin_invs in cdnr_json:
            totals_row_data['total_receiptients']['val'] += 1
            for inv in gstin_invs.get('nt', {}):
                totals_row_data['total_invoices_val']['val'] += inv['val']
                totals_row_data['total_invoices']['val'] += 1
                for item in inv.get('itms', {}):
                    row_data = [
                        {'val': gstin_invs['ctin'], 'column': 'A'},
                        {'val': inv['nt_num'], 'column': 'B'},
                        {'val': datetime.strptime(inv['nt_dt'], '%d-%m-%Y'), 'column': 'C', 'format': cell_formats.get('date')},
                        {'val': inv['ntty'], 'column': 'D'},
                        {'val': inv['pos'], 'column': 'E'},
                        {'val': inv['rchrg'], 'column': 'F'},
                        {'val': inv['val'], 'column': 'G', 'format': cell_formats.get('number')},
                        {'val': item['itm_det']['rt'], 'column': 'H', 'format': cell_formats.get('number')},
                        {'val': item['itm_det']['txval'], 'column': 'I', 'format': cell_formats.get('number')},
                        {'val': item['itm_det']['csamt'], 'column': 'J', 'format': cell_formats.get('number')},
                    ]
                    self._set_spreadsheet_row(worksheet, row_data, row_count, cell_formats.get('regular'))
                    totals_row_data['total_cess']['val'] += item['itm_det']['csamt']
                    totals_row_data['total_taxable_val']['val'] += item['itm_det']['txval']
                    row_count += 1
        self._set_spreadsheet_row(worksheet, totals_row_data, totals_val_row, cell_formats.get('regular'))

    def _prepare_cdnur_sheet(self, cdnur_json, workbook, cell_formats):
        primary_header_row = 2
        secondary_header_row = 4
        totals_val_row = 3
        row_count = 5
        worksheet = workbook.add_worksheet('cdnur')
        worksheet.write('A1', 'Summary For CDNUR(9B)', cell_formats.get('primary_header'))
        primary_headers = [
           {'val': 'No. of Notes/Vouchers', 'column': 'B'},
           {'val': 'Total Note Value', 'column': 'F'},
           {'val': 'Total Taxable Value', 'column': 'H'},
           {'val': 'Total Cess', 'column': 'I'},
        ]
        secondary_headers = [
            {'val': 'UR Type', 'column': 'A'},
            {'val': 'Note Number', 'column': 'B'},
            {'val': 'Note Date', 'column': 'C'},
            {'val': 'Note Type', 'column': 'D'},
            {'val': 'Place Of Supply', 'column': 'E'},
            {'val': 'Note Value', 'column': 'F'},
            {'val': 'Rate', 'column': 'G'},
            {'val': 'Taxable Value', 'column': 'H'},
            {'val': 'Cess Amount', 'column': 'I'},
        ]
        totals_row_data = {
            'total_invoices': {'val': 0, 'column': 'B'},
            'total_invoices_val': {'val': 0, 'column': 'F', 'format': cell_formats.get('number')},
            'total_taxable_val': {'val': 0, 'column': 'H', 'format': cell_formats.get('number')},
            'total_cess': {'val': 0, 'column': 'I', 'format': cell_formats.get('number')},
        }
        self._set_spreadsheet_row(worksheet, primary_headers, primary_header_row)
        self._set_spreadsheet_row(worksheet, secondary_headers, secondary_header_row)
        worksheet.set_row(primary_header_row - 1, None, cell_formats.get('primary_header'))
        worksheet.set_row(secondary_header_row - 1, None, cell_formats.get('secondary_header'))
        worksheet.set_column('A:A', 30)
        worksheet.set_column('B:J', 15)
        for cdnur in cdnur_json:
            totals_row_data['total_invoices_val']['val'] += cdnur['val']
            totals_row_data['total_invoices']['val'] += 1
            for item in cdnur.get('itms', {}):
                row_data = [
                    {'val': cdnur['typ'], 'column': 'A'},
                    {'val': cdnur['nt_num'], 'column': 'B'},
                    {'val': datetime.strptime(cdnur['nt_dt'], '%d-%m-%Y'), 'column': 'C', 'format': cell_formats.get('date')},
                    {'val': cdnur['ntty'], 'column': 'D'},
                    {'val': cdnur.get('pos'), 'column': 'E'},
                    {'val': cdnur['val'], 'column': 'F', 'format': cell_formats.get('number')},
                    {'val': item['itm_det']['rt'], 'column': 'G', 'format': cell_formats.get('number')},
                    {'val': item['itm_det']['txval'], 'column': 'H', 'format': cell_formats.get('number')},
                    {'val': item['itm_det']['csamt'], 'column': 'I', 'format': cell_formats.get('number')},
                ]
                self._set_spreadsheet_row(worksheet, row_data, row_count, cell_formats.get('regular'))
                totals_row_data['total_cess']['val'] += item['itm_det']['csamt']
                totals_row_data['total_taxable_val']['val'] += item['itm_det']['txval']
                row_count += 1
        self._set_spreadsheet_row(worksheet, totals_row_data, totals_val_row, cell_formats.get('regular'))

    def _prepare_exp_sheet(self, exp_json, workbook, cell_formats):
        primary_header_row = 2
        secondary_header_row = 4
        totals_val_row = 3
        row_count = 5
        worksheet = workbook.add_worksheet('exp')
        worksheet.write('A1', 'Summary For EXP(6)', cell_formats.get('primary_header'))
        primary_headers = [
           {'val': 'No. of Invoices', 'column': 'B'},
           {'val': 'Total Invoice Value', 'column': 'D'},
           {'val': 'No. of Shipping Bill', 'column': 'F'},
           {'val': 'Total Taxable Value', 'column': 'I'},
        ]
        secondary_headers = [
            {'val': 'Export Type', 'column': 'A'},
            {'val': 'Invoice Number', 'column': 'B'},
            {'val': 'Invoice Date', 'column': 'C'},
            {'val': 'Invoice Value', 'column': 'D'},
            {'val': 'Port Code', 'column': 'E'},
            {'val': 'Shipping Bill Number', 'column': 'F'},
            {'val': 'Shipping Bill Date', 'column': 'G'},
            {'val': 'Rate', 'column': 'H'},
            {'val': 'Taxable Value', 'column': 'I'},
            {'val': 'Cess Amount', 'column': 'J'},
        ]
        totals_row_data = {
            'total_invoices': {'val': 0, 'column': 'B'},
            'total_invoices_val': {'val': 0, 'column': 'D', 'format': cell_formats.get('number')},
            'total_shipping_bills': {'val': 0, 'column': 'F'},
            'total_taxable_val': {'val': 0, 'column': 'I', 'format': cell_formats.get('number')},
        }
        self._set_spreadsheet_row(worksheet, primary_headers, primary_header_row)
        self._set_spreadsheet_row(worksheet, secondary_headers, secondary_header_row)
        worksheet.set_row(primary_header_row - 1, None, cell_formats.get('primary_header'))
        worksheet.set_row(secondary_header_row - 1, None, cell_formats.get('secondary_header'))
        worksheet.set_column('A:A', 30)
        worksheet.set_column('B:J', 15)
        for exp in exp_json:
            for inv in exp.get('inv', {}):
                for item in inv.get('itms', {}):
                    row_data = [
                        {'val': exp['exp_typ'], 'column': 'A'},
                        {'val': inv['inum'], 'column': 'B'},
                        {'val': datetime.strptime(inv['idt'], '%d-%m-%Y'), 'column': 'C', 'format': cell_formats.get('date')},
                        {'val': inv['val'], 'column': 'D', 'format': cell_formats.get('number')},
                        {'val': inv.get('sbpcode'), 'column': 'E'},
                        {'val': inv.get('sbnum'), 'column': 'F'},
                        {'val': inv.get('sbdt') and datetime.strptime(inv.get('sbdt'), '%d-%m-%Y'), 'column': 'G', 'format': cell_formats.get('date')},
                        {'val': item['rt'], 'column': 'H', 'format': cell_formats.get('number')},
                        {'val': item['txval'], 'column': 'I', 'format': cell_formats.get('number')},
                        {'val': item['csamt'], 'column': 'J', 'format': cell_formats.get('number')},
                    ]
                    self._set_spreadsheet_row(worksheet, row_data, row_count, cell_formats.get('regular'))
                    totals_row_data['total_taxable_val']['val'] += item['txval']
                    row_count += 1
                totals_row_data['total_invoices']['val'] += 1
                totals_row_data['total_shipping_bills']['val'] += (inv.get('sbnum') and 1) or 0
                totals_row_data['total_invoices_val']['val'] += inv['val']
        self._set_spreadsheet_row(worksheet, totals_row_data, totals_val_row, cell_formats.get('regular'))

    def _prepare_nil_sheet(self, nil_json, workbook, cell_formats):
        primary_header_row = 2
        secondary_header_row = 4
        totals_val_row = 3
        row_count = 5
        worksheet = workbook.add_worksheet('nil')
        worksheet.write('A1', 'Summary For Nil rated, exempted and non GST outward supplies (8)', cell_formats.get('primary_header'))
        primary_headers = [
           {'val': 'Total Nil Rated Supplies', 'column': 'B'},
           {'val': 'Total Exempted Supplies', 'column': 'C'},
           {'val': 'Total Non-GST Supplies', 'column': 'D'},
        ]
        secondary_headers = [
           {'val': 'Description', 'column': 'A'},
           {'val': 'Nil Rated Supplies', 'column': 'B'},
           {'val': 'Exempted Supplies', 'column': 'C'},
           {'val': 'Non-GST Supplies', 'column': 'D'},
        ]
        totals_row_data = {
            'total_nil_rated': {'val': 0, 'column': 'B', 'format': cell_formats.get('number')},
            'total_exempt': {'val': 0, 'column': 'C', 'format': cell_formats.get('number')},
            'total_nongst': {'val': 0, 'column': 'D', 'format': cell_formats.get('number')},
        }
        self._set_spreadsheet_row(worksheet, primary_headers, primary_header_row)
        self._set_spreadsheet_row(worksheet, secondary_headers, secondary_header_row)
        worksheet.set_row(primary_header_row - 1, None, cell_formats.get('primary_header'))
        worksheet.set_row(secondary_header_row - 1, None, cell_formats.get('secondary_header'))
        worksheet.set_column('A:A', 30)
        worksheet.set_column('B:J', 20)
        for inv in nil_json.get('inv', {}):
            row_data = [
                {'val': inv['sply_ty'], 'column': 'A'},
                {'val': inv['nil_amt'], 'column': 'B', 'format': cell_formats.get('number')},
                {'val': inv['expt_amt'], 'column': 'C', 'format': cell_formats.get('number')},
                {'val': inv['ngsup_amt'], 'column': 'D', 'format': cell_formats.get('number')},
            ]
            self._set_spreadsheet_row(worksheet, row_data, row_count, cell_formats.get('regular'))
            totals_row_data['total_nil_rated']['val'] += inv['nil_amt']
            totals_row_data['total_exempt']['val'] += inv['expt_amt']
            totals_row_data['total_nongst']['val'] += inv['ngsup_amt']
            row_count += 1
        self._set_spreadsheet_row(worksheet, totals_row_data, totals_val_row, cell_formats.get('regular'))

    def _prepare_hsn_sheet(self, hsn_json, workbook, cell_formats):
        primary_header_row = 2
        secondary_header_row = 4
        totals_val_row = 3
        row_count = 5
        worksheet = workbook.add_worksheet('hsn')
        worksheet.write('A1', 'Summary For HSN(12)', cell_formats.get('primary_header'))
        primary_headers = [
           {'val': 'No. of HSN', 'column': 'A'},
           {'val': 'Total Value', 'column': 'D'},
           {'val': 'Total Taxable Value', 'column': 'F'},
           {'val': 'Total Integrated Tax', 'column': 'G'},
           {'val': 'Total Central Tax', 'column': 'H'},
           {'val': 'Total State/UT Tax', 'column': 'I'},
           {'val': 'Total Cess', 'column': 'J'},
        ]
        secondary_headers = [
            {'val': 'HSN', 'column': 'A'},
            {'val': 'UQC', 'column': 'B'},
            {'val': 'Total Quantity', 'column': 'C'},
            {'val': 'Total Value', 'column': 'D'},
            {'val': 'Rate', 'column': 'E'},
            {'val': 'Taxable Value', 'column': 'F'},
            {'val': 'Integrated Tax Amount', 'column': 'G'},
            {'val': 'Central Tax Amount', 'column': 'H'},
            {'val': 'State/UT Tax Amount', 'column': 'I'},
            {'val': 'Cess Amount', 'column': 'J'},
        ]
        totals_row_data = {
            'total_hsn': {'val': 0, 'column': 'A', 'row':3},
            'total_value': {'val': 0, 'column': 'D', 'row':3, 'format': cell_formats.get('number')},
            'total_taxable_val': {'val': 0, 'column': 'F', 'row':3, 'format': cell_formats.get('number')},
            'total_igst': {'val': 0, 'column': 'G', 'row':3, 'format': cell_formats.get('number')},
            'total_cgst': {'val': 0, 'column': 'H', 'row':3, 'format': cell_formats.get('number')},
            'total_sgst': {'val': 0, 'column': 'I', 'row':3, 'format': cell_formats.get('number')},
            'total_cess': {'val': 0, 'column': 'J', 'row':3, 'format': cell_formats.get('number')},
        }
        self._set_spreadsheet_row(worksheet, primary_headers, primary_header_row)
        self._set_spreadsheet_row(worksheet, secondary_headers, secondary_header_row)
        worksheet.set_row(primary_header_row - 1, None, cell_formats.get('primary_header'))
        worksheet.set_row(secondary_header_row - 1, None, cell_formats.get('secondary_header'))
        worksheet.set_column('A:A', 30)
        worksheet.set_column('B:J', 20)
        for item in hsn_json.get('data', {}):
            total_val = item['txval'] + item['iamt'] + item['samt'] + item['camt'] + item['csamt']
            row_data = [
                {'val': item['hsn_sc'], 'column': 'A'},
                {'val': item['uqc'], 'column': 'B'},
                {'val': item['qty'], 'column': 'C', 'format': cell_formats.get('number')},
                {'val': total_val, 'column': 'D', 'format': cell_formats.get('number')},
                {'val': item['rt'], 'column': 'E', 'format': cell_formats.get('number')},
                {'val': item['txval'], 'column': 'F', 'format': cell_formats.get('number')},
                {'val': item['iamt'], 'column': 'G', 'format': cell_formats.get('number')},
                {'val': item['camt'], 'column': 'H', 'format': cell_formats.get('number')},
                {'val': item['samt'], 'column': 'I', 'format': cell_formats.get('number')},
                {'val': item['csamt'], 'column': 'J', 'format': cell_formats.get('number')},
            ]
            self._set_spreadsheet_row(worksheet, row_data, row_count, cell_formats.get('regular'))
            totals_row_data['total_hsn']['val'] += 1
            totals_row_data['total_value']['val'] += total_val
            totals_row_data['total_taxable_val']['val'] += item['txval']
            totals_row_data['total_igst']['val'] += item['iamt']
            totals_row_data['total_cgst']['val'] += item['camt']
            totals_row_data['total_sgst']['val'] += item['samt']
            totals_row_data['total_cess']['val'] += item['csamt']
            row_count += 1
        self._set_spreadsheet_row(worksheet, totals_row_data, totals_val_row, cell_formats.get('regular'))
