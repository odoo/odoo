# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class CalendarEvent(models.Model):
    """ Model for Calendar Event """
    _inherit = 'calendar.event'

    @api.model
    def default_get(self, fields):
        if self.env.context.get('default_applicant_id'):
            self = self.with_context(
                default_res_model='hr.applicant', #res_model seems to be lost without this
                default_res_model_id=self.env.ref('hr_recruitment.model_hr_applicant').id,
                default_res_id=self.env.context['default_applicant_id'],
                default_partner_ids=self.env.context['default_partner_ids'],
                default_name=self.env.context['default_name']
            )

        defaults = super(CalendarEvent, self).default_get(fields)

        # sync res_model / res_id to opportunity id (aka creating meeting from lead chatter)
        if 'applicant_id' not in defaults:
            res_model = defaults.get('res_model', False) or self.env.context.get('default_res_model')
            res_model_id = defaults.get('res_model_id', False) or self.env.context.get('default_res_model_id')
            if (res_model and res_model == 'hr.applicant') or (res_model_id and self.env['ir.model'].sudo().browse(res_model_id).model == 'hr.applicant'):
                defaults['applicant_id'] = defaults.get('res_id', False) or self.env.context.get('default_res_id', False)

        return defaults

    def _compute_is_highlighted(self):
        super(CalendarEvent, self)._compute_is_highlighted()
        applicant_id = self.env.context.get('active_id')
        if self.env.context.get('active_model') == 'hr.applicant' and applicant_id:
            for event in self:
                if event.applicant_id.id == applicant_id:
                    event.is_highlighted = True

    applicant_id = fields.Many2one('hr.applicant', string="Applicant", index='btree_not_null', ondelete='set null')
