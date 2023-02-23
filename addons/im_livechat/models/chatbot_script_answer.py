# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models, fields
from odoo.osv import expression

import textwrap


class ChatbotScriptAnswer(models.Model):
    _name = 'chatbot.script.answer'
    _description = 'Chatbot Script Answer'
    _order = 'script_step_id, sequence, id'

    name = fields.Char(string='Answer', required=True, translate=True)
    sequence = fields.Integer(string='Sequence', default=1)
    redirect_link = fields.Char('Redirect Link',
        help="The visitor will be redirected to this link upon clicking the option "
             "(note that the script will end if the link is external to the livechat website).")
    script_step_id = fields.Many2one(
        'chatbot.script.step', string='Script Step', required=True, ondelete='cascade')
    chatbot_script_id = fields.Many2one(related='script_step_id.chatbot_script_id')

    def name_get(self):
        if self._context.get('chatbot_script_answer_display_short_name'):
            return super().name_get()

        result = []
        for answer in self:
            answer_message = answer.script_step_id.message.replace('\n', ' ')
            shortened_message = textwrap.shorten(answer_message, width=26, placeholder=" [...]")

            result.append((
                answer.id,
                "%s: %s" % (shortened_message, answer.name)
            ))

        return result

    @api.model
    def _name_search(self, name='', args=None, operator='ilike', limit=100, name_get_uid=None):
        """
        Search the records whose name or step message are matching the ``name`` pattern.
        The chatbot_script_id is also passed to the context through the custom widget
        ('chatbot_triggering_answers_widget') This allows to only see the question_answer
        from the same chatbot you're configuring.
        """
        force_domain_chatbot_script_id = self.env.context.get('force_domain_chatbot_script_id')

        if name and operator == 'ilike':
            if not args:
                args = []

            # search on both name OR step's message (combined with passed args)
            name_domain = [('name', operator, name)]
            step_domain = [('script_step_id.message', operator, name)]
            domain = expression.AND([args, expression.OR([name_domain, step_domain])])

        else:
            domain = args or []

        if force_domain_chatbot_script_id:
            domain = expression.AND([domain, [('chatbot_script_id', '=', force_domain_chatbot_script_id)]])

        return self._search(domain, limit=limit, access_rights_uid=name_get_uid)
