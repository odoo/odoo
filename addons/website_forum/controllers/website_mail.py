# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo.http import route
from odoo.addons.website_mail.controllers.main import WebsiteMail


class ForumWebsiteMail(WebsiteMail):
    _FORUM_MODELS = ("forum.tag", "forum.post")

    def _subscribe_partner(self, record, partner_id, subscribe):
        if record._name not in self._FORUM_MODELS:
            return super()._subscribe_partner(record, partner_id, subscribe)

        record.sudo().is_follower = subscribe

    @route()
    def is_follower(self, records, **post):
        """Overwrite the follower logic for the forum models, that does not inherit from `mail.thread`."""
        forum_records = {
            model: ids for model, ids in records.items() if model in self._FORUM_MODELS
        }
        non_forum_records = {
            model: ids
            for model, ids in records.items()
            if model not in self._FORUM_MODELS
        }

        user_info, followed_records = super().is_follower(non_forum_records, **post)

        # Fill the forum records
        partner = self._get_user_partner()
        if partner:
            for model, record_ids in forum_records.items():
                domain = [
                    ("id", "in", record_ids),
                    ("follower_ids", "=", partner.id),
                ]
                followed_records[model] = self.env[model].sudo().search(domain).ids

        return user_info, followed_records
