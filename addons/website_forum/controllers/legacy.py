# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import http
from odoo.http import request


class WebsiteForumLegacy(http.Controller):
    """ Retro compatibility layer for legacy endpoint """

    @http.route(['/forum/user/<int:user_id>'], type='http', auth="public", website=True)
    def view_user_forum_profile(self, user_id):
        return request.redirect(f'/profile/user/{user_id}')
