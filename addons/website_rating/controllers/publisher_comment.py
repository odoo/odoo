# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import http
from odoo.http import request
from odoo.tools import plaintext2html, html2plaintext


class PortalChatter(http.Controller):

    @http.route(['/website/rating/comment'], type='json', auth="user", method=['POST'], website=True)
    def publish_rating_comment(self, rating_id, publisher_comment):
        rating = request.env['rating.rating'].browse(int(rating_id))
        comment = plaintext2html(publisher_comment) if publisher_comment else False
        rating.write({'publisher_comment': comment})
        # return to the front-end the created/updated publisher comment
        res = rating.read(['publisher_comment', 'publisher_id', 'publisher_date'])[0]
        # Add a plaintext comment for textarea editing
        res["publisher_comment_plaintext"] = html2plaintext(res["publisher_comment"]) if res["publisher_comment"] else False
        return res
