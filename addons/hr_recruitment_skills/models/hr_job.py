# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, api, fields, models


class HrJob(models.Model):
    _inherit = "hr.job"

    skill_ids = fields.Many2many('hr.skill', string='Skills')

    @api.model
    def action_populate_applicants(self):
        return {
            'name': _('Populate Job Applications'),
            'type': 'ir.actions.act_window',
            'target': 'new',
            'res_model': 'populate.job.applicant',
            'view_mode': 'form',
            'views': [(False, 'form')],
            'context': {
                'default_job_ids': self.env.context.get('search_default_job_id'),
            },
        }

    def _populate_job(self, skill_ids):
        self.ensure_one()
        applicant_fields = self.env['hr.applicant']._get_applicant_fields()
        applicants_domain = [('date_closed', '=', False), ('job_id', '!=', self.id)]
        for skill in skill_ids:
            applicants_domain.append(('skill_ids', 'in', skill.ids))

        job_values = {
            'job_id': self.id,
            'user_id': self.env.user.id,
        }
        create_values = []
        partner_done = self.env['res.partner']
        for applicant in self.env['hr.applicant'].with_context(active_test=False).search(applicants_domain):
            if applicant.partner_id in partner_done:
                continue
            create_values.append({
                **{f: applicant[f].id if isinstance(applicant[f], models.Model) else applicant[f] for f in applicant_fields},
                **job_values,
                'skill_ids': applicant.skill_ids.ids,
            })
            partner_done |= applicant.partner_id
        self.env['hr.applicant'].create(create_values)
