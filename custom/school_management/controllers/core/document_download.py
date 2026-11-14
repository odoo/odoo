import io
import xlsxwriter

from odoo import http
from odoo.http import request
from odoo.exceptions import AccessError, UserError


class UniversityDocumentDownloadController(http.Controller):

    def _get_document(self, document_id, need_report=True, model_name=None):
        """Return (document, error_response). Exactly one of them is None."""
        models_to_check = [model_name] if model_name else [
            'university.report.card',
            'university.transcript',
            'university.transcript.request',
            'university.document',
            'university.exam',
        ]
        document = None
        for m in models_to_check:
            if m in request.env:
                rec = request.env[m].browse(document_id).exists()
                if rec:
                    document = rec
                    break
        if not document:
            return None, request.not_found()
        try:
            document.check_access('read')
            document._check_download_allowed(need_report=need_report)
        except AccessError:
            return None, request.not_found()
        except UserError as e:
            return None, request.make_response(
                str(e),
                headers=[('Content-Type', 'text/plain; charset=utf-8')],
                status=400,
            )
        return document, None

    @staticmethod
    def _file_response(content, content_type, filename):
        return request.make_response(
            content,
            headers=[
                ('Content-Type', content_type),
                ('Content-Disposition', f'attachment; filename="{filename}"'),
                ('Content-Length', str(len(content))),
            ],
        )

    @http.route([
        '/university/document/<int:document_id>/download',
        '/university/document/<string:model_name>/<int:document_id>/download'
    ],
                type='http', auth='user', methods=['GET'])
    def download_pdf(self, document_id, model_name=None, **kwargs):
        document, error = self._get_document(document_id, need_report=True, model_name=model_name)
        if error:
            return error
        if hasattr(document, '_log_download'):
            document._log_download(file_type='PDF')
        pdf_content, _ct = request.env['ir.actions.report']._render_qweb_pdf(
            document._download_report_xmlid, res_ids=document.ids,
        )
        filename = f"{document._name.replace('.', '_')}_{document_id}.pdf"
        return self._file_response(
            pdf_content, 'application/pdf', filename,
        )

    @http.route([
        '/university/document/<int:document_id>/download/xlsx',
        '/university/document/<string:model_name>/<int:document_id>/download/xlsx'
    ],
                type='http', auth='user', methods=['GET'])
    def download_xlsx(self, document_id, model_name=None, **kwargs):
        document, error = self._get_document(document_id, need_report=False, model_name=model_name)
        if error:
            return error
        if hasattr(document, '_log_download'):
            document._log_download(file_type='Excel')

        if hasattr(document, '_generate_xlsx_bytes'):
            content = document._generate_xlsx_bytes()
            filename = f"{document._name.replace('.', '_')}_{document_id}.xlsx"
            return self._file_response(
                content,
                'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                filename,
            )

        sheet_name, headers, rows = document._get_xlsx_data()

        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        sheet = workbook.add_worksheet(str(sheet_name)[:31])  # Excel limit: 31 chars
        bold = workbook.add_format({'bold': True, 'bg_color': '#D9E1F2', 'border': 1})

        for col, header in enumerate(headers):
            sheet.write(0, col, header, bold)
            sheet.set_column(col, col, max(15, len(str(header)) + 4))
        for row_idx, row in enumerate(rows, start=1):
            for col, value in enumerate(row):
                sheet.write(row_idx, col, value if value is not False else '')

        workbook.close()
        filename = f"{document._name.replace('.', '_')}_{document_id}.xlsx"
        return self._file_response(
            output.getvalue(),
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            filename,
        )
