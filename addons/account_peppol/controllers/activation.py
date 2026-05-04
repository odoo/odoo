import logging

from odoo import http
from odoo.http import request
from odoo.tools import verify_hash_signed

_logger = logging.getLogger(__name__)


class PeppolActivationController(http.Controller):

    @http.route('/peppol/activate/<string:auth_type>/<string:url_hash>/<int:error>', type='http', auth='public', website=True)
    def external_activation_page(self, auth_type, url_hash, error):

        payload = verify_hash_signed(
            env=request.env(su=True),
            scope='peppol_activation',
            payload=url_hash
        )
        if not payload:
            _logger.warning("This link has expired or is invalid.")
            return request.not_found()

        company = request.env['res.company'].sudo().browse(payload.get('company_id'))
        err_msg = payload.get('err_msg', "")
        reason = payload.get('reason', None)
        base_url = request.env['ir.config_parameter'].sudo().get_str('web.base.url')
        no_error_url = f"{base_url.rstrip('/')}/peppol/activate/{auth_type}/{url_hash}/0"
        auth_url = ""

        if auth_type == "itsme":
            render_view = 'account_peppol.activate_peppol_view'
            auth_url = company._can_connect("itsme").get('available_auths', {}).get('itsme', {}).get('authorization_url')
        else:
            render_view = ""

        return request.render(render_view, {
            'company_name': company.name,
            'auth_url': auth_url,
            'cbe_url': f"https://kbopub.economie.fgov.be/kbopub/zoeknummerform.html?nummer={company.peppol_endpoint}",
            'error': error == 1,
            'error_msg': err_msg if err_msg else None,
            'no_error_url': no_error_url,
            'reason': reason,
        })
