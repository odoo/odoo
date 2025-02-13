# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, api, Command


class DiscussChannel(models.Model):
    """ Chat Session
        Reprensenting a conversation between users.
        It extends the base method for usage with AI assistant.
    """

    _name = 'discuss.channel'
    _inherit = ['discuss.channel']

    channel_type = fields.Selection(selection_add=[('ai_composer', 'Draft with AI')], ondelete={'ai_composer': 'cascade'})

@api.model
def _get_or_create_chat(self, partners_to, pin=True):
    if len(partners_to) == 0:
        # create a new AI chat
        channel = self.create({
            'channel_member_ids': [
                Command.create({
                    'partner_id': self.env.user.partner_id.id,
                })
            ],
            'channel_type': 'ai_composer',
            'name': 'AI: Record Name',
        })
        return channel
    else:
        return super()._get_or_create_chat()
