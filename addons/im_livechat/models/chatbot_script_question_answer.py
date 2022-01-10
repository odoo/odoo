# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models, fields
from odoo.osv import expression


class ChatbotScriptQuestionAnswer(models.Model):
    _name = 'im_livechat.chatbot.script_question_answer'
    _description = 'Chatbot Script Question Answer'

    name = fields.Char(string='Name')
    sequence = fields.Integer(string='Sequence')
    step_id = fields.Many2one(
        'im_livechat.chatbot.script_step', string='Script Step', required=True, ondelete='cascade')
    chatbot_id = fields.Many2one(related='step_id.chatbot_id', store=True)

    # TODO PKO: Test if conflict with name_get ? not sure why we defined name_get in the first place...
    def _compute_display_name(self):
        for record in self:
            record.display_name = record.name

    def name_get(self):
        return [(
            answer.id, "%s: %s" % (answer.step_id.message, answer.name)
        ) for answer in self]

    @api.model
    def _name_search(self, name, args=None, operator='ilike', limit=100, name_get_uid=None):
        force_domain_chatbot_id = self.env.context.get('force_domain_chatbot_id')

        if name and operator == 'ilike':
            if not args:
                args = []

            # search on both name OR step's message (combined with passed args)
            name_domain = expression.AND([[('name', operator, name)], args])
            step_domain = expression.AND([[('step_id.message', operator, name)], args])
            domain = expression.OR([name_domain, step_domain])

        else:
            domain = args or []

        if force_domain_chatbot_id:
            domain = expression.AND([domain, [('chatbot_id', '=', force_domain_chatbot_id)]])

        return self._search(domain, limit=limit, access_rights_uid=name_get_uid)
