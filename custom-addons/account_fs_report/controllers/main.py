import io, json
import xlsxwriter
from odoo import http
from odoo.http import request
from odoo.http.stream import content_disposition

class FsReportController(http.Controller):

    @http.route('/account_fs_report/export/xlsx', type='http', auth='user')
    def export_xlsx(self, report_id, options, **kw):
        report_id = int(report_id)
        options = json.loads(options)
        data = request.env['fs.report.engine'].get_report_data(report_id, options)
        rows = data['lines'] if isinstance(data, dict) else data
        report = request.env['fs.report'].browse(report_id)
        buf = io.BytesIO()
        wb = xlsxwriter.Workbook(buf, {'in_memory': True})
        ws = wb.add_worksheet(report.name[:31])
        # Match Enterprise account_reports figure/name styling:
        # level 0 bold + gray fill; zeros muted; negatives red.
        title_fmt = wb.add_format({'bold': True, 'font_name': 'Lato', 'font_size': 12})
        header_fmt = wb.add_format({'bold': True, 'font_name': 'Lato', 'font_size': 12, 'font_color': '#666666'})
        name_l0 = wb.add_format({
            'bold': True, 'font_name': 'Lato', 'font_size': 13, 'font_color': '#666666',
            'bg_color': '#dee2e6',
        })
        name_default = wb.add_format({'font_name': 'Lato', 'font_size': 12, 'font_color': '#666666'})
        num_default = wb.add_format({'font_name': 'Lato', 'font_size': 12, 'font_color': '#666666', 'num_format': '#,##0.00'})
        num_l0 = wb.add_format({
            'bold': True, 'font_name': 'Lato', 'font_size': 13, 'font_color': '#666666',
            'num_format': '#,##0.00', 'bg_color': '#dee2e6',
        })
        num_muted = wb.add_format({'font_name': 'Lato', 'font_size': 12, 'font_color': '#adb5bd', 'num_format': '#,##0.00'})
        num_muted_l0 = wb.add_format({
            'bold': True, 'font_name': 'Lato', 'font_size': 13, 'font_color': '#adb5bd',
            'num_format': '#,##0.00', 'bg_color': '#dee2e6',
        })
        num_neg = wb.add_format({'font_name': 'Lato', 'font_size': 12, 'font_color': '#dc3545', 'num_format': '#,##0.00'})
        num_neg_l0 = wb.add_format({
            'bold': True, 'font_name': 'Lato', 'font_size': 13, 'font_color': '#dc3545',
            'num_format': '#,##0.00', 'bg_color': '#dee2e6',
        })
        ws.write(0, 0, report.name, title_fmt)
        for i, col in enumerate(options['columns']):
            ws.write(1, i + 1, col['label'], header_fmt)
        r = 2
        for row in rows:
            if row['hide_if_zero'] and not any(row['columns']):
                continue
            is_l0 = row['level'] == 0
            ws.write(r, 0, '    ' * row['level'] + row['name'], name_l0 if is_l0 else name_default)
            for i, v in enumerate(row['columns']):
                if abs(v) < 1e-9:
                    fmt = num_muted_l0 if is_l0 else num_muted
                elif v < 0:
                    fmt = num_neg_l0 if is_l0 else num_neg
                else:
                    fmt = num_l0 if is_l0 else num_default
                ws.write_number(r, i + 1, v, fmt)
            r += 1
        ws.set_column(0, 0, 45)
        ws.set_column(1, len(options['columns']), 18)
        wb.close()
        file_name = report.get_default_report_filename(options, 'xlsx')
        return request.make_response(buf.getvalue(), headers=[
            ('Content-Type', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'),
            ('Content-Disposition', content_disposition(file_name)),
        ])

    @http.route('/account_fs_report/export/pdf', type='http', auth='user')
    def export_pdf(self, report_id, options, **kw):
        report_id = int(report_id)
        options = json.loads(options)
        data = request.env['fs.report.engine'].get_report_data(report_id, options)
        rows = data['lines'] if isinstance(data, dict) else data
        report = request.env['fs.report'].browse(report_id)
        pdf, _ = request.env['ir.actions.report']._render_qweb_pdf(
            'account_fs_report.report_fs_pdf', res_ids=[report_id],
            data={'rows': rows, 'options': options, 'title': report.name})
        file_name = report.get_default_report_filename(options, 'pdf')
        return request.make_response(pdf, headers=[
            ('Content-Type', 'application/pdf'),
            ('Content-Disposition', content_disposition(file_name)),
        ])
