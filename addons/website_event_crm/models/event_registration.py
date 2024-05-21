# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, _
from markupsafe import Markup


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
            answer_value = Markup("<br/>").join(["    %s" % line for line in answer_value.split('\n')])
            answer_descriptions.append(Markup("  - %s<br/>%s") % (answer.question_id.title, answer_value))
        return Markup("%s%s<br/>%s") % (reg_description, _("Questions"), Markup('<br/>').join(answer_descriptions))

    def _get_lead_description_fields(self):
        res = super(EventRegistration, self)._get_lead_description_fields()
        res.append('registration_answer_ids')
        return res

    def _get_lead_grouping(self, rules, rule_to_new_regs):
        visitor_registrations = self.filtered('visitor_id')
        # We don't want to group by visitor if there is a sale order, this is done here to avoid
        # another bridge module.
        if self._fields.get('sale_order_id'):
            visitor_registrations -= visitor_registrations.filtered('sale_order_id')
        grouping_res = super(EventRegistration, self - visitor_registrations)._get_lead_grouping(rules, rule_to_new_regs)

        if visitor_registrations:
            related_registrations = self.env['event.registration'].search([
                ('visitor_id', 'in', visitor_registrations.visitor_id.ids)
            ])
            related_leads = self.env['crm.lead'].search([
                ('event_lead_rule_id', 'in', rules.ids),
                ('registration_ids', 'in', related_registrations.ids),
            ])

            for rule in rules:
                rule_new_regs = rule_to_new_regs[rule]
                visitor_to_regs = (rule_new_regs & visitor_registrations).grouped('visitor_id')
                visitor_res = []
                for visitor, registrations in visitor_to_regs.items():
                    registrations = registrations.sorted('id')
                    leads = related_leads.filtered(lambda lead: lead.event_lead_rule_id == rule and lead.registration_ids.visitor_id == visitor)
                    visitor_res.append((leads, visitor, registrations))
                if visitor_res:
                    grouping_res[rule] = grouping_res.get(rule, list()) + visitor_res

        return grouping_res

    def _get_lead_values(self, rule):
        """Update lead values from Lead Generation rules to include the visitor and their language"""
        lead_values = super()._get_lead_values(rule)
        lead_values.update({
            'visitor_ids': self.visitor_id,
            'lang_id': self.visitor_id.lang_id.id,
        })
        return lead_values
