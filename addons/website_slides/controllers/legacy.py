# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import http
from odoo.http import request


class WebsiteSlidesLegacy(http.Controller):
    """
        Retro compatibility layer for legacy endpoint
    """

    @http.route(['/slides/all', '/slides/all/tag/<string:slug_tags>'], type='http', auth="public", website=True,
                sitemap=False, readonly=True)
    def slides_channel_all(self, slug_tags=None, **post):
        """ "All" in < 19 was different from "Home". Both have been merged, but we keep
        some backward compatibility for saved links, even if the display is going to
        change a bit. """
        if slug_tags:
            post['tags'] = slug_tags
        return request.redirect_query('/slides', query=post)
