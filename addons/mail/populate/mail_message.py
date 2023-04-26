# -*- coding: utf-8 -*-
from odoo import models
from odoo.tools import populate

class Message(models.Model):
    _inherit = 'mail.message'
    _populate_dependencies = ['discuss.channel', 'discuss.channel.member', 'res.partner']
    _populate_sizes = {'small': 1000, 'medium': 10000, 'large': 500000}

    def _populate_factories(self):
        channel_ids = self.env.registry.populated_models['discuss.channel']

        def get_author_id(values, counter, random):
            channel = self.env[values['model']].browse(values['res_id'])
            channel_member_ids = [channel['id'] for channel in channel.channel_member_ids.read(['id'])]
            return random.choice(channel_member_ids)

        return [
            ('body', populate.constant('message_body_{counter}')),
            ('message_type', populate.constant('comment')),
            ('model', populate.constant('discuss.channel')),
            ('res_id', populate.randomize(channel_ids)),
            ('author_id', populate.compute(get_author_id)),
        ]

    def _populate(self, size):
        partner = self.env.ref('base.user_admin').partner_id
        # create 100 in the chatter of the res.partner admin
        messages = []
        for counter in range(100):
            messages.append({
                'body': f'message_body_{counter}',
                'message_type': 'comment',
                'model': 'res.partner',
                'res_id': partner.id,
                'author_id': partner.id,
            })
        self.env['mail.message'].create(messages)
        return super()._populate(size)
