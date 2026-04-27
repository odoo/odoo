# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import defaultdict

from odoo import api, fields, models


class AppointmentType(models.Model):
    _inherit = "appointment.type"

    lead_create = fields.Boolean(string="Create Opportunities",
        help="For each scheduled appointment, create a new opportunity and assign it to the responsible user.")
    lead_ids = fields.Many2many('crm.lead', string="Leads/Opportunity", compute="_compute_lead_ids", groups="sales_team.group_sale_salesman")
    lead_count = fields.Integer('Leads Count', compute="_compute_lead_ids", groups="sales_team.group_sale_salesman")

    @api.depends('meeting_ids', 'meeting_ids.opportunity_id')
    @api.depends_context('allowed_company_ids')
    def _compute_lead_ids(self):
        allowed_company_ids = [False, *self.env.context.get('allowed_company_ids', [])]
        appointment_lead_data = self.env['calendar.event'].sudo()._read_group(
            [('appointment_type_id', 'in', self.ids), ('opportunity_id.company_id', 'in', allowed_company_ids)],
            ['appointment_type_id', 'opportunity_id'],
        )
        appointment_lead_mapped_data = defaultdict(list)
        for appointment_type, opportunity in appointment_lead_data:
            appointment_lead_mapped_data[appointment_type.id].append(opportunity.id)

        for appointment in self:
            lead_ids = appointment_lead_mapped_data[appointment.id]
            leads = self.env['crm.lead'].browse(lead_ids)._filtered_access('read')
            appointment.lead_ids = leads
            appointment.lead_count = len(leads)

    def action_appointment_leads(self):
        self.ensure_one()
        action = self.env['ir.actions.act_window']._for_xml_id('crm.crm_lead_opportunities')
        action['domain'] = [('id', 'in', self.lead_ids.ids)]
        action['context'] = dict(default_type='opportunity', create=False)
        return action

    @api.model
    def _get_calendar_view_appointment_type_default_context_fields_whitelist(self):
        """ Add the opportunity_id field to list of fields we accept as default in context """
        whitelist_fields = super()._get_calendar_view_appointment_type_default_context_fields_whitelist()
        whitelist_fields.append('opportunity_id')
        return whitelist_fields
