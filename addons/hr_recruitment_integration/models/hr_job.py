# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, SUPERUSER_ID, _


class Job(models.Model):
    _name = "hr.job"
    _inherit = "hr.job"

    job_post_count = fields.Integer(compute="_compute_job_post_count")

    def _compute_job_post_count(self):
        job_posts = self.env['hr.job.post']._read_group([], ['job_id'], ['__count'])
        mapped_count = {job.id: count for job, count in job_posts}
        for job in self:
            job.job_post_count = mapped_count.get(job.id, 0)

    def action_post_job(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Post Job'),
            'res_model': 'hr.recruitment.post.job',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_job_id': self.id,
                        'default_job_title': self.name,
                        'default_job_apply_mail': self.alias_full_name,
                        'dialog_size': 'medium'},
            'views': [[False, 'form']]
        }

    def action_open_job_posts(self):
        return {
            'type': 'ir.actions.act_window',
            'name': _('Job Posts'),
            'res_model': 'hr.job.post',
            'view_mode': 'tree',
            'target': 'self',
            'domain': [('job_id', '=', self.id)],
            'views': [(self.env.ref('hr_recruitment_integration.hr_job_post_tree').id, 'tree')]
        }
