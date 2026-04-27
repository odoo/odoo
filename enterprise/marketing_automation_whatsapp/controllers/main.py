from werkzeug.exceptions import NotFound

from odoo import http
from odoo.http import request


class MarketingAutomationWhatsappController(http.Controller):

    @http.route('/r/<string:code>/w/<int:whatsapp_id>', type='http', auth="public")
    def whatsapp_short_link_redirect(self, code, whatsapp_id, **post):
        wa_message_id = request.env['whatsapp.message'].sudo().browse(whatsapp_id).exists().id

        request.env['link.tracker.click'].sudo().add_click(
            code,
            ip=request.httprequest.remote_addr,
            country_code=request.geoip.country_code,
            whatsapp_message_id=wa_message_id
        )
        redirect_url = request.env['link.tracker'].get_url_from_code(code)
        if not redirect_url:
            raise NotFound()
        return request.redirect(redirect_url, code=301, local=False)
