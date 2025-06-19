from odoo import http
from odoo.http import request, content_disposition


class DownloadFA3Controller(http.Controller):

    @http.route('/l10n_pl_edi/download/<int:move_id>', type='http', auth='user')
    def download_fa3_xml(self, move_id, **kwargs):
        """
        Controller to generate and download the FA(3) XML file for a given invoice.
        """
        invoice = request.env['account.move'].browse(move_id)
        invoice.check_access_rights('read')

        xml_data = invoice._l10n_pl_ksef_render_xml()
        filename = f"FA3-{invoice.name.replace('/', '_')}.xml"

        return request.make_response(
            xml_data,
            headers=[
                ('Content-Type', 'application/xml'),
                ('Content-Disposition', content_disposition(filename)),
            ])
