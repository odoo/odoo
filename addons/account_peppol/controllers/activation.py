from odoo import http
from odoo.http import request


class PeppolActivationController(http.Controller):

    @http.route('/peppol/activate/<string:auth_type>/<string:url_hash>/<int:error>', type='http', auth='public', website=True)
    def external_activation_page(self, auth_type, url_hash, error):

        # find the correct company, then find the correct registration for that company (multiple might exist, get the newest one)
        company = request.env['res.company'].sudo().search([]).filtered(lambda c: c._get_portal_hash() == url_hash)
        if not company:
            return request.not_found()

        registration = request.env['peppol.registration'].sudo().search([
            ('company_id', '=', company.id),
        ], limit=1, order='id desc')

        if not registration:
            registration = self.env['peppol.registration'].with_context(flow='new').create({'company_id': company.id})

        base_url = request.env['ir.config_parameter'].sudo().get_str('web.base.url')
        no_error_url = f"{base_url.rstrip('/')}/peppol/activate/{auth_type}/{url_hash}/0"

        if auth_type == "itsme":
            render_view = 'account_peppol.activate_peppol_view'
        else:
            render_view = ""

        return request.render(render_view, {
            'company_name': registration.company_id.name,
            'auth_url': registration.peppol_new_auth_url,
            'cbe_url': f"https://kbopub.economie.fgov.be/kbopub/zoeknummerform.html?nummer={registration.peppol_endpoint}",
            'error': error == 1,
            'no_error_url': no_error_url
        })
