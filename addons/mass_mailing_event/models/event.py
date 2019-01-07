# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class Event(models.Model):
    _inherit = "event.event"

    def action_mass_mailing_attendees(self):
        if len(self) == 1:
            domain = "[('event_id', '=', {})]".format(self.id)
        else:
            domain = "[('event_id', 'in', {})]".format(self.ids)
        mass_mailing_action = dict(
            name='Mass Mail Attendees',
            type='ir.actions.act_window',
            res_model='mail.mass_mailing',
            view_type='form',
            view_mode='form',
            target='current',
            context=dict(
                default_mailing_model_id=self.env.ref('event.model_event_registration').id,
                default_mailing_domain=domain,
            ),
        )
        return mass_mailing_action
