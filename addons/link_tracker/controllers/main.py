# Part of Odoo. See LICENSE file for full copyright and licensing details.

from werkzeug.exceptions import NotFound

from odoo import http
from odoo.http import request


class LinkTracker(http.Controller):

    @http.route('/r/<string:code>', type='http', auth='public', website=True)
    def full_url_redirect(self, code, **post):
        # Link preview requests must not be counted as clicks.
        is_link_preview = request.httprequest.headers.get('Odoo-Link-Preview')
        # WhatsApp link previews are not bots, but they are not clicks either
        user_agent = request.httprequest.user_agent.string.lower()
        if not is_link_preview and not request.env['ir.http'].is_a_bot() and 'whatsapp/' not in user_agent:
            request.env['link.tracker.click'].sudo().add_click(
                code,
                ip=request.httprequest.remote_addr,
                country_code=request.geoip.country_code,
            )
        redirect_url = request.env['link.tracker'].get_url_from_code(code)
        if not redirect_url:
            raise NotFound()
        return request.redirect(redirect_url, code=301, local=False)
