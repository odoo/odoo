# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, _


class EventRegistration(models.Model):
    _inherit = 'event.registration'

    def _get_lead_description(self, prefix):
        """Add the questions and answers linked to the registrations into the description of the lead."""
        description = super(EventRegistration, self)._get_lead_description(prefix)
        if self.registration_answer_ids:
            description += _("Questions:\n")
            for answer in self.registration_answer_ids:
                answer_value = answer.value_answer_id.name if answer.question_type == "simple_choice" else answer.value_text_box
                answer_value = "\n".join(["\t%s" % line for line in answer_value.split('\n')])
                description += "- %s\n%s\n" % (answer.question_id.title, answer_value)
        return description

    def _get_lead_specific_vals(self):
        old_registration_vals = super(EventRegistration, self)._get_lead_specific_vals()
        return {**old_registration_vals, **{'registration_answer_ids': self.registration_answer_ids.ids}}
