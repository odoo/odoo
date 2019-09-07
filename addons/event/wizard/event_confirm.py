# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, api


class event_confirm(models.TransientModel):
    """Event Confirmation"""
    _name = "event.confirm"
    _description = 'Event Confirmation'

    def confirm(self):
        events = self.env['event.event'].browse(self._context.get('event_ids', []))
        events.do_confirm()
        return {'type': 'ir.actions.act_window_close'}
