# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import http, _
from odoo.http import request


class PortalRating(http.Controller):

    @http.route(['/website/rating/comment'], type='json', auth="user", methods=['POST'], website=True)
    def publish_rating_comment(self, rating_id, publisher_comment):
        rating = request.env['rating.rating'].search_fetch(
            [('id', '=', int(rating_id))],
            ['publisher_comment', 'publisher_id', 'publisher_datetime'],
        )
        if not rating:
            return {'error': _('Invalid rating')}
        rating.write({'publisher_comment': publisher_comment})
        # return to the front-end the created/updated publisher comment
        return request.env['mail.message']._portal_message_format_rating(
            rating.read(['publisher_comment', 'publisher_id', 'publisher_datetime'])[0]
        )
