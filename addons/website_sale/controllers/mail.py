# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.portal.controllers.mail import MailController


class WebsiteSaleMailController(MailController):

    def _get_public_chatter_url_data(self, message):
        if message.model == "product.template":
            return {"url": f"/shop/{message.res_id}"}
        return super()._get_public_chatter_url_data(message)
