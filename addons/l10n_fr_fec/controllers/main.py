from odoo.http import Controller, request, route, Response


class FecDownloadController(Controller):
    @route('/download/fec_file/<int:wizard_id>', type='http', auth='user')
    def download_fec(self, wizard_id):
        wizard = request.env['account.fr.fec'].browse(wizard_id)
        return Response(
            wizard._get_fec_stream(),
            headers=[
                ('Content-Type', 'text/csv'),
                ('Content-Disposition', f'attachment; filename={wizard.filename};')
            ],
            direct_passthrough=True
        )
