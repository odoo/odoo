# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.http import request
from odoo.addons.portal.controllers.mail import MailController


class WebsiteBlogMailController(MailController):

    def _get_public_chatter_url_data(self, message):
        if message.model == "blog.post" and (post := request.env["blog.post"].browse(message.res_id)):
            {"url": f"/blog/{post.blog_id.id}/{post.id}"}
        return super()._get_public_chatter_url_data(message)
