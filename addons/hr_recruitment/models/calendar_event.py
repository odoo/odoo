# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class CalendarEvent(models.Model):
    """ Model for Calendar Event """
    _inherit = 'calendar.event'

    def _compute_is_highlighted(self):
        res = self._is_highlighted(False, False)
        applicant_id = self.env.context.get('active_id')
        for event in self:
            if self.env.context.get('active_model') == 'hr.applicant' and applicant_id:
                applicant = self.env['hr.applicant'].browse(applicant_id)
                if applicant.meeting_ids.filtered(lambda s: s.id == event.id):
                    event.is_highlighted = True
            else:
                event.is_highlighted = res.get(event.id)

    @api.model
    def create(self, vals):
        res = super(CalendarEvent, self).create(vals)
        applicant_id = self.env.context.get('active_id')
        if self.env.context.get('active_model') == 'hr.applicant' and applicant_id:
            self.env['hr.applicant'].browse(applicant_id).write({'meeting_ids': [(4, res.id)]})
        return res

    is_highlighted = fields.Boolean(compute="_compute_is_highlighted", string='# Meetings Highlight')
