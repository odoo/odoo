# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class CalendarEvent(models.Model):
    _inherit = 'calendar.event'

    @api.model
    def default_get(self, fields):
        self_ctx = self
        if self.env.context.get('default_applicant_id'):
            self_ctx = self.with_context(
                default_res_model='hr.applicant',  # res_model seems to be lost without this
                default_res_model_id=self.env.ref('hr_recruitment.model_hr_applicant').id,
                default_res_id=self.env.context.get('default_applicant_id'),
                default_partner_ids=self.env.context.get('default_partner_ids'),
                default_name=self.env.context.get('default_name')
            )
        elif self.env.context.get('default_candidate_id'):
            self_ctx = self.with_context(
                default_res_model='hr.candidate',  # res_model seems to be lost without this
                default_res_model_id=self.env.ref('hr_recruitment.model_hr_candidate').id,
                default_res_id=self.env.context.get('default_candidate_id'),
                default_partner_ids=self.env.context.get('default_partner_ids'),
                default_name=self.env.context.get('default_name')
            )

        defaults = super(CalendarEvent, self_ctx).default_get(fields)

        # sync res_model / res_id to opportunity id (aka creating meeting from lead chatter)
        if 'applicant_id' not in defaults:
            res_model = defaults.get('res_model', False) or self_ctx.env.context.get('default_res_model')
            res_model_id = defaults.get('res_model_id', False) or self_ctx.env.context.get('default_res_model_id')
            if (res_model and res_model == 'hr.applicant') or (res_model_id and self_ctx.env['ir.model'].sudo().browse(res_model_id).model == 'hr.applicant'):
                defaults['applicant_id'] = defaults.get('res_id', False) or self_ctx.env.context.get('default_res_id', False)

        return defaults

    applicant_id = fields.Many2one('hr.applicant', string="Applicant", index='btree_not_null', ondelete='set null')
    candidate_id = fields.Many2one(
        'hr.candidate',
        string="Candidate",
        compute="_compute_candidate_id",
        store=True,
        readonly=False,
        index='btree_not_null',
        ondelete='set null')

    @api.model_create_multi
    def create(self, vals_list):
        events = super().create(vals_list)
        if not self.env['hr.applicant'].has_access('read'):
            return events

        attachments = False
        if "default_applicant_id" in self.env.context:
            attachments = self.env['hr.applicant'].browse(self.env.context['default_applicant_id']).attachment_ids
        elif "default_candidate_id" in self.env.context:
            attachments = self.env['hr.candidate'].browse(self.env.context['default_candidate_id']).attachment_ids
        if attachments:
            self.env['ir.attachment'].create([{
                'name': att.name,
                'type': 'binary',
                'datas': att.datas,
                'res_model': event._name,
                'res_id': event.id
            } for event in events for att in attachments])
        return events

    def _compute_is_highlighted(self):
        super()._compute_is_highlighted()
        applicant_id = self.env.context.get('active_id')
        if self.env.context.get('active_model') == 'hr.applicant' and applicant_id:
            for event in self:
                if event.applicant_id.id == applicant_id:
                    event.is_highlighted = True

    @api.depends('applicant_id')
    def _compute_candidate_id(self):
        for event in self:
            if not event.applicant_id:
                continue
            event.candidate_id = event.applicant_id.candidate_id
