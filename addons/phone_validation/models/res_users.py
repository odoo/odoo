# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, models
from odoo.addons.phone_validation.tools import phone_validation


class Users(models.Model):
    _inherit = 'res.users'

    def _deactivate_portal_user(self, **post):
        """Blacklist the phone of the user after deleting it."""
        numbers_to_blacklist = {}  # numbers to blacklist and the related user
        if post.get('request_blacklist'):
            for user in self:
                sanitized = phone_validation.phone_sanitize_numbers_w_record([user.phone, user.mobile], user)
                user_phone = sanitized[user.phone]['sanitized']
                user_mobile = sanitized[user.mobile]['sanitized']
                if user_phone:
                    numbers_to_blacklist[user_phone] = user
                if user_mobile:
                    numbers_to_blacklist[user_mobile] = user

        super(Users, self)._deactivate_portal_user(**post)

        if numbers_to_blacklist:
            current_user = self.env.user
            blacklists = self.env['phone.blacklist']._add(
                list(numbers_to_blacklist.keys()))
            for blacklist in blacklists:
                user = numbers_to_blacklist[blacklist.number]
                blacklist._message_log(
                    body=_('Blocked by deletion of portal account %(portal_user_name)s by %(user_name)s (#%(user_id)s)',
                           user_name=current_user.name, user_id=current_user.id,
                           portal_user_name=user.name),
                )
