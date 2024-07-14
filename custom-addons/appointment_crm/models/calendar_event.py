# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from markupsafe import Markup

from odoo import api, fields, models, Command, _


class CalendarEventCrm(models.Model):
    _inherit = 'calendar.event'

    opportunity_id = fields.Many2one(compute="_compute_opportunity_id", readonly=False, store=True, tracking=True)

    @api.depends('appointment_invite_id')
    def _compute_opportunity_id(self):
        for event in self:
            if event.appointment_invite_id.opportunity_id:
                event.opportunity_id = event.appointment_invite_id.opportunity_id

    @api.model_create_multi
    def create(self, vals_list):
        events = super().create(vals_list)
        # We want only event with the right appointment type and another attendee than the employee
        events.filtered(
            lambda e: e.appointment_type_id.lead_create and e.partner_ids - e.user_id.partner_id
        ).sudo()._create_lead_from_appointment()
        opportunity_field = self.env['ir.model.fields']._get("calendar.event", "opportunity_id")
        for meeting in events.filtered('opportunity_id'):
            meeting._message_log(
                body=Markup("<p>%s</p>") % _(
                    "Meeting linked to Lead/Opportunity %s",
                    meeting.opportunity_id._get_html_link()),
                tracking_value_ids=[Command.create({
                    'field_id': opportunity_field.id,
                    'old_value_char': False,
                    'new_value_char': meeting.opportunity_id.name,
                })])
        return events

    def _create_lead_from_appointment(self):
        lead_values = []
        for event in self:
            partner = event.partner_ids - event.user_id.partner_id
            lead_values.append(event._get_lead_values(partner[:1]))

        # Create leads within the event organizer's company
        leads = self.env['crm.lead'].with_context(mail_create_nosubscribe=True) \
            .with_company(self.user_id.company_id).create(lead_values)
        for event, lead in zip(self, leads):
            event._link_with_lead(lead)
            lead.activity_schedule(
                act_type_xmlid='mail.mail_activity_data_meeting',
                date_deadline=event.start_date,
                summary=event.name,
                user_id=event.user_id.id,
                calendar_event_id=event.id
            )
        return leads

    def _get_lead_values(self, partner):
        appointment_tag = self.env.ref('appointment_crm.appointment_crm_tag', raise_if_not_found=False)
        return {
            'name': self.name,
            'tag_ids': [Command.link(appointment_tag.id)] if appointment_tag else False,
            'partner_id': partner.id,
            'type': 'opportunity',
            'user_id': self.user_id.id,
            'description': self.description,
        }

    def _link_with_lead(self, lead):
        self.write({
            'res_model_id': self.env['ir.model']._get(lead._name).id,
            'res_id': lead.id,
            'opportunity_id': lead.id,
        })
