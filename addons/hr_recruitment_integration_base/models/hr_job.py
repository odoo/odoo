# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import defaultdict

from odoo import models, fields, _


class Job(models.Model):
    _inherit = 'hr.job'

    job_post_count = fields.Integer(
        compute='_compute_job_post_count', string='Number of Job Posts')

    def _compute_job_post_count(self):
        counts_by_job_id = defaultdict(int)
        counts_by_job_id.update(
            dict(
                self.env['hr.job.post']._read_group(
                    domain=[('job_id', 'in', self.ids)],
                    groupby=['job_id'],
                    aggregates=['__count'],
                )
            )
        )
        for job in self:
            job.job_post_count = counts_by_job_id[job.id]

    def action_post_job(self):
        self.ensure_one()
        return {
            'name': _('Post Job'),
            'type': 'ir.actions.act_window',
            'res_model': 'hr.job.post',
            'view_mode': 'form',
            'target': 'new',
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
