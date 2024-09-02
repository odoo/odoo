# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models
from odoo.osv import expression


class ChatbotScriptStep(models.Model):
    _inherit = 'chatbot.script.step'

    def _fetch_next_step(self, selected_answer_ids):
        """ Fetch the next step depending on the user's last selected answer.
            If a step contains multiple triggering answers from the same step or from different steps
            the condition between them must be a 'OR'.
            A step can trigger steps that have a lower sequence than itself (allowing to do go back
            in the dialogue and to do loops)

            e.g:

            STEP 1 : A B
            STEP 2 : C D
            STEP 3 : E
            STEP 4 ONLY IF A C

            Scenario 1 (B C E):

            B in (A) -> NOK
            C in (C) -> OK

            -> OK

            Scenario 2 (B D E):

            B in (A) -> NOK
            D in (C) -> NOK

            -> NOK
        """
        self.ensure_one()

        if self.env['im_livechat.channel.rule'].search([('chatbot_script_id', '=', self.chatbot_script_id.id)], limit=1).is_script_flexible:
            last_answer = selected_answer_ids[0] if selected_answer_ids else None

            domain = [('chatbot_script_id', '=', self.chatbot_script_id.id)]
            if selected_answer_ids:
                domain = expression.AND([domain, [
                    '|',
                    ('triggering_answer_ids', '=', False),
                    ('triggering_answer_ids', 'in', [last_answer.id])]])

            if last_answer and not last_answer in self.triggering_answer_ids:
                steps = self.env['chatbot.script.step'].search(domain)
                for step in steps:
                    if last_answer in step.triggering_answer_ids:
                        return step

            domain = expression.AND([domain, [('sequence', '>', self.sequence)]])
            steps = self.env['chatbot.script.step'].search(domain)
            for step in steps:
                if (last_answer and last_answer in step.triggering_answer_ids) \
                        or not step.triggering_answer_ids:
                    return step

            return self.env['chatbot.script.step']

        else:
            return super()._fetch_next_step(selected_answer_ids)
