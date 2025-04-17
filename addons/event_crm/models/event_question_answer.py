from odoo import models


class EventQuestionAnswer(models.Model):
    _inherit = 'event.question.answer'

    def action_add_rule_button(self):
        self.ensure_one()
        action = self.env['ir.actions.actions']._for_xml_id('event_crm.event_lead_rule_answer_action')
        action['context'] = {
            'default_name': self.name,
            'default_lead_user_id': self.env.user.id,
            'default_event_registration_filter': [
                '&',
                ('registration_answer_ids.question_id', 'ilike', self.question_id.title),
                ('registration_answer_choice_ids', 'ilike', self.name)
            ]
        }
        action['target'] = 'new'
        return action
