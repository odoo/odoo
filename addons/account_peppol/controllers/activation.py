from odoo import http
from odoo.http import request


class PeppolActivationController(http.Controller):

    @http.route('/peppol/activate/<string:auth_type>/<string:url_hash>/<int:error>', type='http', auth='public', website=True)
    def external_activation_page(self, auth_type, url_hash, error):

        # Find the correct company
        company = request.env['res.company'].sudo().search([]).filtered(lambda c: c._get_portal_hash() == url_hash)
        if not company:
            return request.not_found()

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
            'no_error_url': no_error_url
        })
