# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, _
from odoo.exceptions import UserError


class Applicant(models.Model):

    _inherit = 'hr.applicant'

    def website_form_input_filter(self, request, values):
        if 'partner_name' in values:
            applicant_job = self.env['hr.job'].sudo().search([('id', '=', values['job_id'])]).name if 'job_id' in values else False
            name = '%s - %s' % (values['partner_name'], applicant_job) if applicant_job else _("%s's Application", values['partner_name'])
            values.setdefault('name', name)
        if values.get('job_id'):
            job = self.env['hr.job'].browse(values.get('job_id'))
            if not job.sudo().active:
                raise UserError(_("The job offer has been closed."))
            stage = self.env['hr.recruitment.stage'].sudo().search([
                ('fold', '=', False),
                '|', ('job_ids', '=', False), ('job_ids', '=', values['job_id']),
            ], order='sequence asc', limit=1)
            if stage:
                values['stage_id'] = stage.id
        return values

    def _notify_get_recipients_groups(self, message, model_description, msg_vals=None):
        groups = super()._notify_get_recipients_groups(message, model_description, msg_vals=msg_vals)
        if msg_vals['email_layout_xmlid'] != 'mail.mail_notification_layout':
            return groups
        customer_group = next(group for group in groups if group[0] == 'customer')
        customer_group[2].update({
            'active': True,
            'has_button_access': True
        })
        access_opt = customer_group[2].setdefault('button_access', {'title': _('Job Description')})
        access_opt['url'] = self._notify_get_action_link('controller', controller=self.job_id.website_url, **msg_vals)
        return groups
