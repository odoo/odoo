# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, _


class EventRegistration(models.Model):
    _inherit = 'event.registration'

    def _get_lead_description_registration(self, line_suffix=''):
        """Add the questions and answers linked to the registrations into the description of the lead."""
        reg_description = super(EventRegistration, self)._get_lead_description_registration(line_suffix=line_suffix)
        if not self.registration_answer_ids:
            return reg_description

        answer_descriptions = []
        for answer in self.registration_answer_ids:
            answer_value = answer.value_answer_id.name if answer.question_type == "simple_choice" else answer.value_text_box
            answer_value = "<br/>".join(["    %s" % line for line in answer_value.split('\n')])
            answer_descriptions.append("  - %s<br/>%s" % (answer.question_id.title, answer_value))
        return "%s%s<br/>%s" % (reg_description, _("Questions"), '<br/>'.join(answer_descriptions))

    def _get_lead_description_fields(self):
        res = super(EventRegistration, self)._get_lead_description_fields()
        res.append('registration_answer_ids')
        return res

    def _get_lead_values(self, rule):
        """Update lead values from Lead Generation rules to include the visitor and their language"""
        lead_values = super()._get_lead_values(rule)
        lead_values.update({
            'visitor_ids': self.visitor_id,
            'lang_id': self.visitor_id.lang_id.id,
        })
        return lead_values
