# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields


class MailMessageReaction(models.Model):
    _name = 'mail.message.reaction'
    _description = 'Message Reaction'
    _order = 'id desc'

    message_id = fields.Many2one('mail.message', 'Message', ondelete='cascade', required=True, readonly=1)
    emoji_unicode = fields.Char("Emoji", required=True, readonly=1)
    reactor_id = fields.Many2one('res.partner', 'Reactor', ondelete='cascade', required=True, readonly=1)

    _sql_constraints = [
        ('unique_message_emoji_reactor', 'unique (message_id, emoji_unicode, reactor_id)', 'One reactor should not have the same reaction twice on a message.')
    ]

    def reaction_format(self):
        res_list = self._read_format(["id", "message_id", "emoji_unicode"])
        for res, reaction in zip(res_list, self):
            res["reactor"] = [("insert", {'id': reaction.reactor_id.id, 'name': reaction.reactor_id.name})]
        return res_list
