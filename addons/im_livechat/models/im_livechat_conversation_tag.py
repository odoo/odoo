# Part of Odoo. See LICENSE file for full copyright and licensing details.

from random import randint

from odoo import fields, models, api, Command


class Im_LivechatConversationTag(models.Model):
    """Tags for Live Chat conversations."""

    _name = "im_livechat.conversation.tag"
    _description = "Live Chat Conversation Tags"
    _order = "name"

    @api.model
    def _get_default_color(self):
        return randint(1, 11)

    name = fields.Char("Name", required=True)
    color = fields.Integer("Color", default=_get_default_color)
    conversation_ids = fields.Many2many(
        "discuss.channel",
        "livechat_conversation_tag_rel",
        string="Discuss Channels",
    )

    _name_unique = models.UniqueIndex("(name)")

    @api.ondelete(at_uninstall=False)
    def _unlink_sync_conversation(self):
        # For triggering the _sync_field_names before being unlinked
        # sudo: users who can delete tags can remove them from conversations in cascade
        self.sudo().conversation_ids.livechat_conversation_tag_ids = [
            Command.unlink(tag.id) for tag in self
        ]
