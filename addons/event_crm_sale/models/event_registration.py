# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import defaultdict

from odoo import models


class EventRegistration(models.Model):
    _inherit = 'event.registration'

    def _get_lead_grouping(self, rules, rule_to_new_regs):
        """ Override to support sale-order based grouping and update.

        When checking for groups for rules, we search for existing leads linked
        to same group (based on sale_order_id) and rule. Each rule can therefore
        update an existing lead or create a new one, for each sale order that
        makes the group. """
        so_registrations = self.filtered(lambda reg: reg.sale_order_id)
        grouping_res = super(EventRegistration, self - so_registrations)._get_lead_grouping(rules, rule_to_new_regs)

        if so_registrations:
            # find existing leads in batch to put them in cache and avoid multiple search / queries
            related_registrations = self.env['event.registration'].search([
                ('sale_order_id', 'in', so_registrations.sale_order_id.ids)
            ])
            related_leads = self.env['crm.lead'].search([
                ('event_lead_rule_id', 'in', rules.ids),
                ('registration_ids', 'in', related_registrations.ids)
            ])

            for rule in rules:
                rule_new_regs = rule_to_new_regs[rule]

                # for each group (sale_order), find its linked registrations
                so_to_regs = defaultdict(lambda: self.env['event.registration'])
                for registration in rule_new_regs & so_registrations:
                    so_to_regs[registration.sale_order_id] |= registration

                # for each grouped registrations, prepare result with group and existing lead
                so_res = []
                for sale_order, registrations in so_to_regs.items():
                    registrations = registrations.sorted('id')  # as an OR was used, re-ensure order
                    leads = related_leads.filtered(lambda lead: lead.event_lead_rule_id == rule and lead.registration_ids.sale_order_id == sale_order)
                    so_res.append((leads, sale_order, registrations))
                if so_res:
                    grouping_res[rule] = grouping_res.get(rule, list()) + so_res

        return grouping_res
