from odoo.exceptions import AccessDenied
from odoo.http import Controller, request, route, Response


class FecDownloadController(Controller):
    @route('/download/fec_file/<int:wizard_id>', type='http', auth='user')
    def download_fec(self, wizard_id, company_id):
        company_id = int(company_id)
        if company_id not in request.env.user.company_ids.ids:
            raise AccessDenied()
        wizard = request.env['account.fr.fec'].with_company(company_id).browse(wizard_id)
        return Response(
            wizard._get_fec_stream(),
            headers=[
                ('Content-Type', 'text/csv'),
                ('Content-Disposition', f'attachment; filename={wizard.filename};')
            ],
            direct_passthrough=True
        )
