# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.mail.controllers import thread
from odoo import http
from odoo.http import request
from odoo.tools import html2plaintext


class ThreadController(thread.ThreadController):

    @http.route()
    def mail_message_update_content(self, message_id, update_data, **kwargs):
        if rating_value := update_data.pop("rating_value", False):
            domain = [("message_id", "=", message_id)]
            rating = (
                request.env["rating.rating"].sudo().search(domain, order="write_date DESC", limit=1)
            )
            rating.rating = rating_value
            rating.feedback = html2plaintext(update_data.get("body"))
        return super().mail_message_update_content(message_id, update_data, **kwargs)
