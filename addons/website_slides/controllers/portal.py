# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import http
from odoo.http import request
from odoo.addons.portal.controllers.mail import PortalChatter


class SlidesPortalChatter(PortalChatter):

    @http.route(['/mail/chatter_post'], type='http', methods=['POST'], auth='public', website=True)
    def portal_chatter_post(self, res_model, res_id, message, **kw):
        result = super(SlidesPortalChatter, self).portal_chatter_post(res_model, res_id, message, **kw)
        if res_model == 'slide.channel':
            rating_value = kw.get('rating_value', False)
            slide_channel = request.env[res_model].sudo().browse(int(res_id))
            if rating_value and slide_channel and request.env.user.partner_id.id == int(kw.get('pid')):
                # apply karma gain rule only once
                request.env.user.add_karma(slide_channel.karma_gen_channel_rank)
        return result
