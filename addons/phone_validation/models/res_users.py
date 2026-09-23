from odoo import models


class ResUsers(models.Model):
    _inherit = "res.users"

    def _deactivate_portal_user(self, **post):
        """Blacklist the phone of the user after deleting it."""
        numbers_to_blacklist = {}  # numbers to blacklist and the related user
        if post.get("request_blacklist"):
            for user in self:
                for phone in user._phone_get_numbers():
                    if phone.valid:
                        numbers_to_blacklist[phone.sanitized] = user

        super()._deactivate_portal_user(**post)

        if numbers_to_blacklist:
            current_user = self.env.user
            blacklists = self.env["phone.blacklist"]._add(
                list(numbers_to_blacklist.keys())
            )
            for blacklist in blacklists:
                user = numbers_to_blacklist[blacklist.number]
                blacklist._message_log(
                    body=self.env._(
                        "Blocked by deletion of portal account %(portal_user_name)s by %(user_name)s (#%(user_id)s)",
                        user_name=current_user.name,
                        user_id=current_user.id,
                        portal_user_name=user.name,
                    ),
                )
