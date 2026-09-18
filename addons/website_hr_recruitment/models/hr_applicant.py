# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models
from odoo.exceptions import UserError


class HrApplicant(models.Model):
    _inherit = 'hr.applicant'

    def get_base_url(self):
        if self.job_id:
            return self.job_id.get_base_url()
        return super().get_base_url()

    def website_form_input_filter(self, request, values):
        if 'partner_id' in values:
            values.pop('email_from', None)
            values.pop('partner_phone', None)
        if values.get('job_id'):
            job = self.env['hr.job'].browse(values.get('job_id'))
            if not job.sudo().active:
                raise UserError(self.env._("The job opportunity has been closed."))
            stage = self.env['hr.recruitment.stage'].sudo().search([
                ('fold', '=', False),
                '|', ('job_ids', '=', False), ('job_ids', '=', values['job_id']),
            ], order='sequence asc', limit=1)
            if stage:
                values['stage_id'] = stage.id
        return values
