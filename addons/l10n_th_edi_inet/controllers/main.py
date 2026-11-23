# Part of Odoo. See LICENSE file for full copyright and licensing details.

from werkzeug.exceptions import NotFound

from odoo import http
from odoo.http import request


class L10nThEdiInetController(http.Controller):

    @http.route('/l10n_th_edi_inet/rd_status/<string:token>', type='http', auth='public', methods=['POST'], csrf=False, save_session=False)
    def rd_status(self, token):
        if not (document := request.env['l10n_th_edi_inet.document']._l10n_th_edi_inet_get_document_from_token(token)):
            raise NotFound()
        document._l10n_th_edi_inet_update_rd_state(request.get_json_data())
        return request.make_response('', status=204)
