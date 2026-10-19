# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class EventEvent(models.Model):
    _inherit = "event.event"

    def action_mass_mailing_attendees(self):
        # Minimal override: set form view being the one mixing sms and mail (not prioritized one)
        action = super().action_mass_mailing_attendees()
        action['view_id'] = self.env.ref('mass_mailing_sms.mailing_mailing_view_form_mixed').id
        return action

    def action_invite_contacts(self):
        # Minimal override: set form view being the one mixing sms and mail (not prioritized one)
        action = super().action_invite_contacts()
        action['view_id'] = self.env.ref('mass_mailing_sms.mailing_mailing_view_form_mixed').id
        return action
