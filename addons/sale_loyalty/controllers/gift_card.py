# Part of Odoo. See LICENSE file for full copyright and licensing details.

from werkzeug.exceptions import BadRequest, NotFound

from odoo.http import Controller, route
from odoo.tools import email_normalize, single_email_re


class GiftCard(Controller):
    @route("/gift_card/send", type="jsonrpc", auth="public")
    def send_gift_card(self, code, email):
        email = email_normalize(email)
        if not (code and email and single_email_re.match(email)):
            raise BadRequest
        # sudo to allow public users to read it
        gift_card = (
            self
            .env["loyalty.card"]
            .sudo()
            .search([("code", "=", code), ("program_type", "=", "gift_card")], limit=1)
        )
        if not gift_card:
            raise NotFound
        email_template = gift_card._get_default_template()
        sender = gift_card._mail_get_customer()
        email_values = {
            "email_to": email,
            "recipient_ids": [],
            "subject": self.env._(
                "You've received a gift card from %s",
                sender.display_name or gift_card.company_id.name,
            ),
        }
        # Guest send has no valid from (defaults to public user)
        if not email_template.email_from:
            author = gift_card._get_mail_author()
            email_values.update(author_id=author.id, email_from=author.email_formatted)
        email_template.send_mail(gift_card.id, email_values=email_values)
        return True
