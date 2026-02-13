# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class EventEvent(models.Model):
    _inherit = "event.event"

    lead_ids = fields.One2many(
        'crm.lead', 'event_id', string="Leads", groups='sales_team.group_sale_salesman',
        help="Leads generated from this event")
    lead_count = fields.Integer(
        string="# Leads", compute='_compute_lead_count', groups='sales_team.group_sale_salesman')

    @api.depends('lead_ids')
    def _compute_lead_count(self):
        lead_data = self.env['crm.lead'].with_context(active_test=False)._read_group(
            [('event_id', 'in', self.ids)],
            ['event_id'], ['__count'],
        )
        mapped_data = {event.id: count for event, count in lead_data}
        for event in self:
            event.lead_count = mapped_data.get(event.id, 0)

    def action_view_leads(self):
        action = self.env['ir.actions.act_window']._for_xml_id('crm.crm_lead_opportunities')
        action['domain'] = [('event_id', '=', self.id)]
        context = self.env['crm.lead']._evaluate_context_from_action(action)
        action['context'] = context | {'active_test': False}

        # If only one lead, open form view directly, otherwise open the list view
        if self.lead_count == 1:
            lead = self.with_context(active_test=False).lead_ids[:1]
            action['views'] = [(False, 'form')]
            action['res_id'] = lead.id
        else:
            action['views'] = sorted(action['views'], key=lambda view: view[1] != 'list')

        return action

    def action_generate_leads(self, event_lead_rules=False):
        """ Re-generate leads based on event.lead.rules.
        The method is ran synchronously if there is a low amount of registrations, otherwise it
        goes through a CRON job that runs in batches. """

        if not self.env.user.has_group('event.group_event_manager'):
            raise UserError(_("Only Event Managers are allowed to re-generate all leads."))

        registrations_count = self.env['event.registration'].search_count([
            ('event_id', 'in', self.ids),
            ('state', 'not in', ['draft', 'cancel']),
        ])

        if registrations_count <= self.env['event.lead.request']._REGISTRATIONS_BATCH_SIZE:
            leads = self.env['event.registration'].search([
                ('event_id', 'in', self.ids),
                ('state', 'not in', ['draft', 'cancel']),
            ])._apply_lead_generation_rules(event_lead_rules)
            if leads:
                notification = _("Yee-ha, %(leads_count)s Leads have been created!", leads_count=len(leads))
            else:
                notification = _("Aww! No Leads created, check your Lead Generation Rules and try again.")
        else:
            self.env['event.lead.request'].sudo().create([{
                'event_id': event.id,
                'event_lead_rule_ids': event_lead_rules,
            } for event in self])
            self.env.ref('event_crm.ir_cron_generate_leads')._trigger()
            notification = _("Got it! We've noted your request. Your leads will be created soon!")

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'type': 'info',
                'sticky': False,
                'message': notification,
                'next': {'type': 'ir.actions.act_window_close'},  # force a form reload
            }
        }
