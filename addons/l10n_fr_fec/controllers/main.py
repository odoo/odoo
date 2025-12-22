from odoo import http
from odoo.http import request


class FecDownloadController(http.Controller):
    @http.route('/download/fec_file/<int:wizard_id>', type='http', auth='user')
    def download_fec(self, wizard_id):
        wizard = request.env['account.fr.fec'].browse(wizard_id)
        content = wizard._get_fec_stream()

        return request.make_response(content, [
            ('Content-Type', 'text/csv'),
            ('Content-Disposition', f'attachment; filename={wizard.filename};')
        ])
