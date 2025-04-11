# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import http
from odoo.exceptions import AccessError, MissingError
from odoo.http import request
from odoo.addons.purchase.controllers import portal


class CustomerPortal(portal.CustomerPortal):

    @http.route(['/my/purchase/<int:order_id>/download_edi'], auth="public", website=True)
    def portal_my_purchase_order_download_edi(self, order_id=None, access_token=None, **kw):
        """ An endpoint to download EDI file representation."""
        try:
            order_sudo = self._document_check_access('purchase.order', order_id, access_token=access_token)
        except (AccessError, MissingError):
            return request.redirect('/my')

        builders = order_sudo._get_edi_builders()

        # This handles only one builder for now, more can be added in the future
        if len(builders) != 1:
            return request.redirect('/my')

        # return self._embed_edi_attachments(order_sudo, builders)
        builder = builders[0]

        xml_content = builder._export_order(order_sudo)
        download_name = builder._export_invoice_filename(order_sudo)  # works even if it's a SO or PO
        http_headers = [
            ('Content-Type', 'text/xml'),
            ('Content-Length', len(xml_content)),
            ('Content-Disposition', f'attachment; filename={download_name}')
        ]
        return request.make_response(xml_content, headers=http_headers)

