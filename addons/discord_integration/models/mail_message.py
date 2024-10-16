# -*- coding: utf-8 -*-

from odoo import models, api
import requests
from requests.exceptions import RequestException
import logging

_logger = logging.getLogger(__name__)

def get_discord_bot_url(env) -> str | None:
    return env['ir.config_parameter'].sudo().get_param("discuss.discord_bot_url")


def get_discord_bot_key(env) -> str | None:
    return env['ir.config_parameter'].sudo().get_param('discuss.discord_bot_key')


class Message(models.Model):
    _inherit = 'mail.message'

    @api.model_create_multi
    def create(self, values_list):
        # OVERRIDE
        result = super().create(values_list)

        discord_bot_url = get_discord_bot_url(self.env)
        discord_bot_key = get_discord_bot_key(self.env)
        if not discord_bot_url or not discord_bot_key:
            return result

        for value_list in values_list:
            if value_list["message_type"] != "comment" or value_list["model"] != "discuss.channel":
                continue
            value_list["message_id"] = result.id

            Attachment = self.env["ir.attachment"]
            attachments = Attachment.browse([attachment[1] for attachment in value_list["attachment_ids"]])

            attachments_info = []
            for attachment in attachments:
                attachments_info.append((attachment.local_url, attachment.display_name))
            value_list["attachments_info"] = attachments_info

            try:
                requests.post(f'{discord_bot_url}/message/create', json=value_list, headers={'x-api-key': discord_bot_key})
            except RequestException as e:
                _logger.error("Error sending message to discord bot server: %s", e)

        return result

    def write(self, vals):
        # OVERRIDE
        result = super().write(vals)

        discord_bot_url = get_discord_bot_url(self.env)
        discord_bot_key = get_discord_bot_key(self.env)
        if not discord_bot_url or not discord_bot_key:
            return result
        if self.message_type != "comment" or self.model != "discuss.channel":
            return result
        if "body" not in vals:
            return result

        vals["message_id"] = self.id
        vals["author_name"] = self.author_id.name
        vals["author_id"] = self.author_id.id

        try:
            if not vals["body"]:
                requests.post(f'{discord_bot_url}/message/delete', json=vals, headers={'x-api-key': discord_bot_key})
            else:
                requests.post(f'{discord_bot_url}/message/edit', json=vals, headers={'x-api-key': discord_bot_key})
        except RequestException as e:
            _logger.error("Error sending message to discord bot server: %s", e)

        return result

    def _message_reaction(self, content, action):
        # OVERRIDE
        result = super()._message_reaction(content, action)

        discord_bot_url = get_discord_bot_url(self.env)
        discord_bot_key = get_discord_bot_key(self.env)
        if not discord_bot_url or not discord_bot_key:
            return result
        if self.message_type != "comment" or self.model != "discuss.channel":
            return result

        vals = {
            "reactor_id": self.env.user.partner_id.id,
            "message_id": self.id,
            "content": content,
            "action": action
        }

        try:
            requests.post(f'{discord_bot_url}/message/reaction', json=vals, headers={'x-api-key': discord_bot_key})
        except RequestException as e:
            _logger.error("Error sending message to discord bot server: %s", e)

        return result
