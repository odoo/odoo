# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import deque

from odoo import fields, models, _
from odoo.exceptions import UserError


class HrRecruitmentPostJobWizard(models.TransientModel):
    _name = 'hr.recruitment.post.job.wizard'
    _description = 'Post Job'
    _transient_max_count = 0
    _transient_max_hours = 24

    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        if self.env.context.get('active_model') == 'hr.job':
            res['job_id'] = self.env.context.get('active_id')
            job = self.env['hr.job'].browse(res['job_id'])
            if job.alias_id and job.alias_id.alias_full_name:
                res['job_apply_mail'] = job.alias_id.alias_full_name
            elif job.user_id and job.user_id.employee_id:
                res['job_apply_mail'] = job.user_id.work_email
        return res

    campaign_start_date = fields.Date(
        string="Campaign Start Date", default=fields.Date.today(),
        help='The date when the campaign will start.', required=True)
    campaign_end_date = fields.Date(
        string="Campaign End Date",
        help='The date when the campaign will end. If not set, '
        'the campaign will run indefinitely or to the maximum allowed by a platform.')
    job_id = fields.Many2one('hr.job', string="Job")
    job_apply_mail = fields.Char(string="Email")
    apply_method = fields.Selection([
        ('email', 'Send an Email'),
    ], default='email', string="Apply Method")
    platform_ids = fields.Many2many('hr.recruitment.platform', string="Job Board", required=True)
    post_html = fields.Html(string="Post", required=True)
    api_data = fields.Json(string="Data")
    post_ids = fields.Many2many('hr.job.post', 'job_id', string="Job Posts")
    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.company)

    def _pospone_posts(self):
        self.ensure_one()
        posts_to_postpone = deque(
            {
                'job_id': self.job_id.id,
                'post_html': self.post_html,
                'platform_id': platform.id,
                'campaign_start_date': self.campaign_start_date,
                'campaign_end_date': self.campaign_end_date,
                'apply_method': self.apply_method,
                'apply_vector': self.job_apply_mail,
                'status': 'pending',
                'status_message': _(
                    'Campaign will start on %(start_date)s',
                    start_date=self.campaign_start_date
                ),
                'company_id': self.company_id.id,
            } for platform in self.platform_ids
        )
        if self.post_ids:
            if any(post.status in ['success', 'warning'] for post in self.post_ids):
                raise UserError(_('Can\'t postpone posts that are already posted'))
            grouped_posts = {post.platform_id.id: post for post in self.post_ids}
            for platform in self.platform_ids:
                grouped_posts[platform.id].sudo().write(posts_to_postpone.popleft())
            self.post_ids._log_post_modifications(mode=_('updated'))
        else:
            self.env['hr.job.post'].sudo().create(posts_to_postpone)

    def _get_apply_vector(self):
        self.ensure_one()
        if self.apply_method == 'email':
            return self.job_apply_mail
        return ''

    def _post_job(self, responses=None):
        self.ensure_one()

        if not responses:
            responses = {}

        posts = deque(
            {
                'job_id': self.job_id.id,
                'post_html': self.post_html,
                'platform_id': platform_id,
                'campaign_start_date': self.campaign_start_date,
                'campaign_end_date': self.campaign_end_date,
                'apply_method': self.apply_method,
                'apply_vector': self._get_apply_vector(),
                'status': responses[platform_id].get('status', 'failure'),
                'status_message': responses[platform_id].get('status_message', ''),
                'api_data': responses[platform_id].get('data', {}),
                'company_id': self.company_id.id
            } for platform_id in self.platform_ids.ids
        )

        if self.post_ids:
            grouped_posts = {post.platform_id.id: post for post in self.post_ids}
            for platform in self.platform_ids:
                grouped_posts[platform.id].write(posts.popleft())
            self.post_ids._log_post_modifications(mode=_('updated'))
        else:
            self.env['hr.job.post'].sudo().create(posts)

        if self.env.context.get('active_model') in ['hr.job', self._name]:
            return {
                'type': 'ir.actions.act_window',
                'name': _('Job Posts'),
                'res_model': 'hr.job.post',
                'view_mode': 'kanban,list,form',
                'search_view_id': self.env.ref('hr_recruitment_integration_base.hr_job_post_view_kanban_search').id,
                'context': {"search_default_job_id": self.job_id.id},
            }
        return {'type': 'ir.actions.act_window_close'}

    def action_post_job(self):
        self.ensure_one()
        if self.campaign_end_date and self.campaign_start_date > self.campaign_end_date:
            raise UserError(_('Campaign start date can\'t be after campaign end date'))
        if self.campaign_start_date > fields.Date.today():
            return self._pospone_posts()
        return self._post_job()
