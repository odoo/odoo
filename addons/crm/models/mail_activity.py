# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class MailActivity(models.Model):
    _inherit = "mail.activity"

    def action_reschedule_meeting(self):
        action = super(MailActivity, self).action_reschedule_meeting()
        current_opportunity = self.calendar_event_id.opportunity_id if self.calendar_event_id.opportunity_id.type == 'opportunity' else False
        if current_opportunity:
            partner_ids = self.env.user.partner_id.ids
            if current_opportunity.partner_id:
                partner_ids.append(current_opportunity.partner_id.id)
            mode, initial_date = self.calendar_event_id.opportunity_id._get_opportunity_meeting_view_parameters()

            action['context'].update({
                'default_opportunity_id': current_opportunity.id,
                'default_partner_id': current_opportunity.partner_id.id,
                'default_partner_ids': partner_ids,
                'default_team_id': current_opportunity.team_id.id,
                'default_name': current_opportunity.name,
                'default_mode': mode,
                'initial_date': initial_date
            })

        return action
