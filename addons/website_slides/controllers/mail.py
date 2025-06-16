from werkzeug.exceptions import BadRequest, Forbidden, NotFound

from odoo import http
from odoo.http import request
from odoo.tools import consteq


class SlidesMailController(http.Controller):

    def _check_token(self, channel_id, attendee_id, token):
        """ Check access on attendee (slide.channel.partner) record. Either
        a token is given and must match, either no token is given and attendee
        partner must be current user's partner. """
        if not channel_id or not attendee_id:
            raise BadRequest()
        attendee_su = request.env['slide.channel.partner'].sudo().search([
            ('channel_id', '=', channel_id),
            ('id', '=', attendee_id),
        ])
        if not attendee_su:
            raise NotFound()
        if token and not consteq(attendee_su._generate_mailing_token(), token):
            raise Forbidden()
        if not token and not self.env.user._is_public() and self.env.user.partner_id != attendee_su.partner_id:
            raise Forbidden()
        return attendee_su

    @http.route(['/slides/channel/<int:channel_id>/opt_out'], type='http', website=True, auth='public')
    def channel_opt_out_form(self, channel_id, attendee_id=None, token=None):
        print(channel_id, attendee_id, token)
        try:
            attendee_su = self._check_token(channel_id, attendee_id, token)
        except Exception as e:
            print('Cacabom', e)
            print(prout)
            return request.redirect('/odoo')  # todo: generic redirect
        print(attendee_su.partner_id.name)
        return request.render('website_slides.slides_unsubscribe_form', {
            'attendee': attendee_su,
            'attendee_token': token,
            'channel': attendee_su.channel_id,
        })

    @http.route(['/slides/channel/<int:channel_id>/opt_out/confirm'], type='http', methods=['POST'], website=True, auth='public')
    def channel_opt_out_confirm(self, channel_id, attendee_id=None, token=None):
        print(channel_id, attendee_id, token)
        try:
            attendee_su = self._check_token(channel_id, attendee_id, token)
        except Exception as e:
            print('Cacabom', e)
            return request.redirect('/odoo')  # todo: generic redirect
        print(attendee_su.partner_id.name)
        attendee_su.opt_out = True
        return request.render('website_slides.slides_unsubscribe_done', {
            'attendee': attendee_su,
            'attendee_token': token,
            'channel': attendee_su.channel_id,
        })

    # Old unsubscribe
    # ------------------------------------------------------------

    @http.route(['/slides/channel/subscribe'], type='jsonrpc', auth='user', website=True)
    def slide_channel_subscribe(self, channel_id):
        # Presentation Published subtype
        subtype = request.env.ref("website_slides.mt_channel_slide_published", raise_if_not_found=False)
        if subtype:
            return request.env['slide.channel'].browse(channel_id).message_subscribe(
                partner_ids=[request.env.user.partner_id.id], subtype_ids=subtype.ids)
        return True

    @http.route(['/slides/channel/unsubscribe'], type='jsonrpc', auth='user', website=True)
    def slide_channel_unsubscribe(self, channel_id):
        request.env['slide.channel'].browse(channel_id).message_unsubscribe(partner_ids=[request.env.user.partner_id.id])
        return True
