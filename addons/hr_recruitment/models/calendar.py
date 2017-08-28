# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class CalendarEvent(models.Model):
    """ Model for Calendar Event """
    _inherit = 'calendar.event'

    @api.model
    def default_get(self, fields):
        defaults = super(CalendarEvent, self).default_get(fields)
        if 'res_model_id' not in defaults and defaults.get('applicant_id'):
            defaults['res_model_id'] = self.env.ref('model_hr_applicant').id
        if 'res_id' not in defaults and defaults.get('applicant_id'):
            defaults['res_id'] = defaults['applicant_id']
        return defaults

    def _compute_is_highlighted(self):
        super(CalendarEvent, self)._compute_is_highlighted()
        applicant_id = self.env.context.get('active_id')
        if self.env.context.get('active_model') == 'hr.applicant' and applicant_id:
            for event in self:
                if event.applicant_id.id == applicant_id:
                    event.is_highlighted = True

    applicant_id = fields.Many2one('hr.applicant', string="Applicant")

    @api.model
    def create(self, vals):
        res = super(CalendarEvent, self).create(vals)
        applicant_id = self.env.context.get('active_id')
        if self.env.context.get('active_model') == 'hr.applicant' and applicant_id:
            res.applicant_id = applicant_id
        return res
