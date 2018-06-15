# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class Event(models.Model):
    _inherit = "event.event"

    def action_mass_mailing_track_speakers(self):
        mass_mailing_action = dict(
            name='Mass Mail Attendees',
            type='ir.actions.act_window',
            res_model='mail.mass_mailing',
            view_type='form',
            view_mode='form',
            target='current',
            context=dict(
                default_mailing_model_id=self.env.ref('website_event_track.model_event_track').id,
                default_mailing_domain="[('event_id', 'in', %s), ('stage_id.is_cancel', '!=', True)]" % self.ids,
            ),
        )
        return mass_mailing_action
