# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class MailActivity(models.Model):
    _inherit = "mail.activity"

    def action_create_calendar_event(self):
        """ Small override of the action that creates a calendar.

        If the activity is linked to a crm.lead (through the "opportunity_id" field or via
        "res_model" if the event isn't created yet), we include in the action context the default
        values used when scheduling a meeting from the crm.lead form view.
        e.g: It will combine the activity's assigned user, the current user and the lead's customer
        as default attendees of the meeting. """

        action = super(MailActivity, self).action_create_calendar_event()
        lead = self.calendar_event_id.opportunity_id
        if not lead and self.res_model == 'crm.lead' and self.res_id:
            lead = self.env['crm.lead'].browse(self.res_id).exists()
        if lead:
            lead_action_context = lead.action_schedule_meeting(smart_calendar=False).get('context', {})
            if self.calendar_event_id:
                lead_action_context['initial_date'] = self.calendar_event_id.start

            lead_action_context['default_partner_ids'] = list({
                *(action['context']['default_partner_ids'] or []),
                *(lead_action_context['default_partner_ids'] or []),
            })
            action['context'].update(lead_action_context)

        return action
