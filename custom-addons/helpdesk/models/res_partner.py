# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ResPartner(models.Model):
    _inherit = 'res.partner'

    ticket_count = fields.Integer("Tickets", compute='_compute_ticket_count')
    sla_ids = fields.Many2many(
        'helpdesk.sla', 'helpdesk_sla_res_partner_rel',
        'res_partner_id', 'helpdesk_sla_id', string='SLA Policies',
        help="SLA Policies that will automatically apply to the tickets submitted by this customer.")

    def _compute_ticket_count(self):
        all_partners_subquery = self.with_context(active_test=False)._search([('id', 'child_of', self.ids)])

        # group tickets by partner, and account for each partner in self
        groups = self.env['helpdesk.ticket']._read_group(
            [('partner_id', 'in', all_partners_subquery)],
            groupby=['partner_id'], aggregates=['__count'],
        )
        self.ticket_count = 0
        for partner, count in groups:
            while partner:
                if partner in self:
                    partner.ticket_count += count
                partner = partner.with_context(prefetch_fields=False).parent_id

    def action_open_helpdesk_ticket(self):
        action = self.env["ir.actions.actions"]._for_xml_id("helpdesk.helpdesk_ticket_action_main_tree")
        action['context'] = {}
        all_child = self.with_context(active_test=False).search([('id', 'child_of', self.ids)])
        action['domain'] = ['|', ('partner_id', 'in', self.ids), ('partner_id', 'in', all_child.ids)]
        return action
