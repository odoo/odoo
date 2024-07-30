from markupsafe import Markup

from odoo import http
from odoo.http import request


class AccountRequestDocument(http.Controller):

    @http.route(
        '/account/request_document/<token>',
        type='http', auth='public', website=True)
    def request_document(self, token=None):
        document = request.env['account.requested.document'].sudo().search([('token', '=', token)])
        if not document:
            return request.not_found()
        context = {
            'base_url': document.get_base_url(),
            'token': str(token),
            'document': document,
        }

        return request.render('account.request_document_page', context)

    @http.route(
        '/account/upload_document/<token>',
        type='http', auth='public', methods=['POST'])
    def upload_document(self, token, **kwargs):
        document = request.env['account.requested.document'].sudo().search([('token', '=', token)])
        if not document:
            return request.not_found()
        file = request.httprequest.files.getlist('requestFile')[0]
        document._process_uploaded_file(file)
        return Markup("""<script type='text/javascript'>
                    window.open("/account/request_document/%s", "_self");
                </script>""") % (token)
