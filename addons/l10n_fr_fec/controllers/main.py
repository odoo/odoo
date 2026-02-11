from odoo import http
from odoo.exceptions import AccessDenied
from odoo.http import request


class FecDownloadController(http.Controller):
    @http.route('/download/fec_file/<int:wizard_id>', type='http', auth='user')
    def download_fec(self, wizard_id, company_id):
        company_id = int(company_id)
        if company_id not in request.env.user.company_ids.ids:
            raise AccessDenied()
        wizard = request.env['account.fr.fec'].with_company(company_id).browse(wizard_id)
        content = wizard._get_fec_stream()

        return request.make_response(content, [
            ('Content-Type', 'text/csv'),
            ('Content-Disposition', f'attachment; filename={wizard.filename};')
        ])
