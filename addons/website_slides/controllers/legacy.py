# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import http
from odoo.http import request
from odoo.addons.base.models.ir_qweb import keep_query


class WebsiteSlidesLegacy(http.Controller):
    """
        Retro compatibility layer for legacy endpoint
    """

    @http.route(['/slides/all', '/slides/all/tag/<string:slug_tags>'], type='http', auth="public", website=True,
                sitemap=True, readonly=True)
    def slides_channel_all(self, slug_tags=None, **post):
        """ "All" in < 19 was different from "Home". Both have been merged, but we keep
        some backward compatibility for saved links, even if the display is going to
        change a bit. """
        if slug_tags:
            return request.redirect(f"/slides/tag/{slug_tags}?{keep_query('*')}")
        return request.redirect(f"/slides?{keep_query('*')}")
