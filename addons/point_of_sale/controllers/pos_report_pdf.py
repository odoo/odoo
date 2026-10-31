import json

from odoo.http import Controller, request, route
from odoo.http.stream import content_disposition

XLSX_MIME = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'


class PosReportPDFController(Controller):

    @route('/pos_reports', type='http', auth='user', methods=['POST'])
    def download_pos_report_pdf(self, report_id=None, model=None, export_format='pdf', options=None, **kwargs):
        if report_id:
            report = request.env['pos.report'].browse(int(report_id))
        else:
            report = request.env['pos.report'].search([('handler_model_name', '=', model)], limit=1)
        if not report.exists():
            return request.make_response(
                json.dumps({'error': 'Report not found'}),
                headers=[('Content-Type', 'application/json')],
                status=404,
            )

        report = report.with_context(**json.loads(options) if options else {})
        try:
            if export_format == 'xlsx':
                result = report.export_to_xlsx()
                file_content = result['file_content']
                file_name = result['file_name']
                headers = [
                    ('Content-Type', XLSX_MIME),
                    ('Content-Disposition', content_disposition(file_name)),
                    ('Content-Length', str(len(file_content))),
                ]
            else:
                result = report.export_to_pdf()
                file_content = result['file_content']
                file_name = result['file_name']
                headers = [
                    ('Content-Type', 'application/pdf'),
                    ('Content-Disposition', content_disposition(file_name)),
                    ('Content-Length', str(len(file_content))),
                ]

            return request.make_response(file_content, headers=headers)

        except Exception as e:  # noqa: BLE001
            return request.make_response(
                json.dumps({'error': str(e)}),
                headers=[('Content-Type', 'application/json')],
                status=500,
            )
