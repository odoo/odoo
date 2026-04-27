# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _


class Job(models.Model):
    _inherit = 'hr.job'

    job_post_count = fields.Integer(
        compute='_compute_job_post_count', string='Number of Job Posts')
    job_post_ids = fields.One2many('hr.job.post', 'job_id', string='Job Posts')
    currency_id = fields.Many2one(
        'res.currency', related='company_id.currency_id', readonly=True)
    salary_min = fields.Monetary('Minimum Salary', currency_field='currency_id')
    salary_max = fields.Monetary('Maximum Salary', currency_field='currency_id')
    payment_interval = fields.Selection([
        ('hourly', 'Hour'),
        ('daily', 'Day'),
        ('weekly', 'Week'),
        ('biweekly', 'Bi-Week'),
        ('monthly', 'Month'),
        ('yearly', 'Year'),
    ], string='Salary Time Unit', default='monthly')
    schedule_id = fields.Many2one('resource.calendar', string='Working Schedule')

    @api.depends('job_post_ids')
    def _compute_job_post_count(self):
        for job in self:
            open_posts = job.job_post_ids.filtered(lambda post: post.status != 'deleted')
            job.job_post_count = len(open_posts)

    @api.onchange('salary_min', 'salary_max', 'payment_interval')
    def _onchange_salary(self):
        if self.salary_min > self.salary_max:
            self.salary_min, self.salary_max = self.salary_max, self.salary_min

    def action_post_job(self):
        self.ensure_one()
        return {
            'name': _('Publish on a Job Board'),
            'type': 'ir.actions.act_window',
            'res_model': 'hr.recruitment.post.job.wizard',
            'view_mode': 'form',
            'target': 'new',
        }
