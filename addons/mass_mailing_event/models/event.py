# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class Event(models.Model):
    _inherit = "event.event"

    def action_mass_mailing_attendees(self):
        mass_mailing_action = dict(
            name='Mass Mail Attendees',
            type='ir.actions.act_window',
            res_model='mail.mass_mailing',
            view_type='form',
            view_mode='form',
            target='current',
            context=dict(
                default_mailing_model='event.registration',
                default_mailing_domain="[('event_id', 'in', %s)]" % self.ids,  # , ('state', 'in', ['draft', 'open', 'done'])
            ),
        )
        return mass_mailing_action