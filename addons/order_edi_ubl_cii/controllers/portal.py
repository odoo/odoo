from odoo.http import request
from odoo.addons.portal.controllers import portal


class CustomerPortal(portal.CustomerPortal):
    def _embed_edi_attachments(self, order, edi_builders=None):
        # This handles only one builder for now, more can be added in the future
        builder = edi_builders[0]

        xml_content = builder._export_order(order)
        download_name = builder._export_invoice_filename(order)     # works even if it's a SO or PO
        http_headers = [
            ('Content-Type', 'text/xml'),
            ('Content-Length', len(xml_content)),
            ('Content-Disposition', f'attachment; filename={download_name}')
        ]
        return request.make_response(xml_content, headers=http_headers)
