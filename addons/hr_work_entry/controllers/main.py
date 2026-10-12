from odoo import http
from odoo.http import request


class HrWorkEntry(http.Controller):

    @http.route('/hr_work_entry/download/<int:company_id>/<int:work_entry_export_id>', type='http', auth='user')
    def download_document(self, company_id, work_entry_export_id):
        export = self.env['hr.export.work.entries'].search([('id', 'in', work_entry_export_id)])
        file = export._generate_export_file(company_id)
        filename = export._generate_export_filename()
        return request.make_response(
            bytes(file),
            headers=[
                ('Content-Type', 'text/plain'),
                ('Content-Disposition', f'attachment; filename={filename + ".txt"};')
            ]
        )
