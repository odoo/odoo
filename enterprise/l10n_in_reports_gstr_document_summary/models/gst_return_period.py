# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import defaultdict

from odoo import models, fields

from .gstr_document_summary import DOCUMENT_TYPE_LIST


class L10nInGstReturnPeriod(models.Model):
    _inherit = 'l10n_in.gst.return.period'

    document_summary_line_ids = fields.One2many('l10n_in.gstr.document.summary.line', 'return_period_id')

    def action_generate_document_summary(self):
        self.document_summary_line_ids.unlink()
        for doc_type, doc_domain in self._get_gst_doc_type_domain().items():
            grouped_data = self.env['account.move'].with_context(
                allowed_company_ids=(self.company_ids or self.company_id).ids
            ).read_group(
                domain=doc_domain,
                fields=[
                    'id:count',
                    'min_name:min(name)',
                    'max_name:max(name)',
                    'sequence_prefix',
                ],
                groupby=['sequence_prefix', 'state'],
                lazy=False
            )
            summary_map = {}
            for group in grouped_data:
                prefix = group['sequence_prefix']
                state = group['state']
                summary = summary_map.setdefault(prefix, {
                    'min_name': group['min_name'],
                    'max_name': group['max_name'],
                    'total_issued': 0,
                    'total_cancelled': 0
                })
                summary['min_name'] = min(summary['min_name'], group['min_name'])
                summary['max_name'] = max(summary['max_name'], group['max_name'])
                summary['total_issued'] += group['__count']
                if state == 'cancel':
                    summary['total_cancelled'] += group['__count']
            self.document_summary_line_ids.create([
                {
                    'return_period_id': self.id,
                    'nature_of_document': doc_type,
                    'serial_from': values['min_name'],
                    'serial_to': values['max_name'],
                    'total_issued': values['total_issued'],
                    'total_cancelled': values['total_cancelled'],
                }
                for prefix, values in summary_map.items()
            ])
        return self.action_open_document_summary()

    def action_open_document_summary(self):
        context = {'default_return_period_id': self.id}
        if self.gstr1_status == 'filed':
            context.update({
                'create': False, 'edit': False, 'delete': False
            })
        return {
            'name': 'GSTR Document Summary',
            'type': 'ir.actions.act_window',
            'res_model': 'l10n_in.gstr.document.summary.line',
            'view_mode': 'list',
            'context': context,
            'domain': [('return_period_id', '=', self.id)],
        }

    def _get_gst_doc_type_domain(self):
        base_domain = [
            ("name", "not in", [False, '/', '']),
            ("posted_before", "=", True),
            ("date", ">=", self.start_date),
            ("date", "<=", self.end_date),
            ("state", "in", ["posted", "cancel"]),
        ]
        return {
            '1': base_domain + [('move_type', '=', 'out_invoice'), ('debit_origin_id', "=", False)],
            '4': base_domain + [('move_type', '=', 'out_invoice'), ('debit_origin_id', "!=", False)],
            '5': base_domain + [('move_type', '=', 'out_refund')]
        }

    def _get_doc_issue_json(self):
        """
        This method returns the doc_issue JSON (Table 13) as below.
        Here, data is grouped by nature of document and serial range.
            {
            'doc_det': [{
                    'doc_num': 1,
                    'docs': [
                        {
                            'num': 1,
                            'from': invoice.name,
                            'to': invoice.name,
                            'totnum': 1,
                            'cancel': 0,
                            'net_issue': 1,
                        }
                    ]
                }]
            }
        """
        result = super()._get_doc_issue_json()
        doc_map = defaultdict(list)
        for line in self.document_summary_line_ids:
            doc_map[int(line.nature_of_document)].append(line)
        doc_det = [
            {
                'doc_num': doc_num,
                'docs': [
                    {
                        'num': idx,
                        'from': line.serial_from,
                        'to': line.serial_to,
                        'totnum': line.total_issued,
                        'cancel': line.total_cancelled,
                        'net_issue': line.total_issued - line.total_cancelled,
                    } for idx, line in enumerate(lines, 1)
                ]
            } for doc_num, lines in sorted(doc_map.items())
        ]
        result['doc_det'] = doc_det
        return result

    def _prepare_sheet_values(self, gstr1_json, workbook, cell_formats):
        super()._prepare_sheet_values(gstr1_json, workbook, cell_formats)
        self._prepare_doc_issue_sheet(gstr1_json.get('doc_issue', {}), workbook, cell_formats)

    def _prepare_doc_issue_sheet(self, doc_issue_json, workbook, cell_formats):
        primary_header_row = 2
        secondary_header_row = 4
        totals_val_row = 3
        row_count = 5
        worksheet = workbook.add_worksheet('docs')
        worksheet.write('A1', 'Summary of documents issued during the tax period (13)', cell_formats.get('primary_header'))
        primary_headers = [
            {'val': 'Total Documents Issued', 'column': 'D'},
            {'val': 'Total Cancelled', 'column': 'E'},
            {'val': 'Total Net Issued', 'column': 'F'},
        ]
        secondary_headers = [
            {'val': 'Nature of Document', 'column': 'A'},
            {'val': 'Sr. No. From', 'column': 'B'},
            {'val': 'Sr. No. To', 'column': 'C'},
            {'val': 'Total Issued', 'column': 'D'},
            {'val': 'Cancelled', 'column': 'E'},
            {'val': 'Net Issued', 'column': 'F'},
        ]
        totals_row_data = {
            'total_issued': {'val': 0, 'column': 'D'},
            'cancelled': {'val': 0, 'column': 'E'},
            'net_issued': {'val': 0, 'column': 'F'},
        }
        self._set_spreadsheet_row(worksheet, primary_headers, primary_header_row, cell_formats.get('primary_header'))
        self._set_spreadsheet_row(worksheet, secondary_headers, secondary_header_row, cell_formats.get('secondary_header'))
        worksheet.set_row(primary_header_row - 1, None, cell_formats.get('primary_header'))
        worksheet.set_row(secondary_header_row - 1, None, cell_formats.get('secondary_header'))
        worksheet.set_column('A:A', 50)
        worksheet.set_column('B:F', 25)
        document_type_selection = dict(DOCUMENT_TYPE_LIST)
        for document in doc_issue_json.get("doc_det", []):
            doc_num = str(document.get("doc_num"))
            for doc in document.get("docs", []):
                row_data = [
                    {'val': document_type_selection.get(doc_num, f'Document {doc_num}'), 'column': 'A'},
                    {'val': doc.get('from', '0'), 'column': 'B'},
                    {'val': doc.get('to', '0'), 'column': 'C'},
                    {'val': doc.get('totnum', 0), 'column': 'D'},
                    {'val': doc.get('cancel', 0), 'column': 'E'},
                    {'val': doc.get('net_issue', 0), 'column': 'F'},
                ]
                self._set_spreadsheet_row(worksheet, row_data, row_count, cell_formats.get('regular'))
                totals_row_data['total_issued']['val'] += doc.get('totnum', 0)
                totals_row_data['cancelled']['val'] += doc.get('cancel', 0)
                totals_row_data['net_issued']['val'] += doc.get('net_issue', 0)
                row_count += 1
        self._set_spreadsheet_row(worksheet, totals_row_data, totals_val_row, cell_formats.get('regular'))
