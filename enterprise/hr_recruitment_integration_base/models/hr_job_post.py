# Part of Odoo. See LICENSE file for full copyright and licensing details.

from markupsafe import Markup

from odoo import fields, models, _
from odoo.exceptions import RedirectWarning


class JobPost(models.Model):
    _name = "hr.job.post"
    _description = "Job Post"
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = "write_date desc"

    job_id = fields.Many2one(
        'hr.job', string="Job", required=True, readonly=True)
    recruiter_id = fields.Many2one(
        'res.users', string="Recruiter", related='job_id.user_id', readonly=True)
    platform_id = fields.Many2one(
        'hr.recruitment.platform', string="Platform",
        required=True, readonly=True)
    platform_icon = fields.Binary(related="platform_id.avatar_128", export_string_translation=False)
    apply_method = fields.Selection([
        ('email', 'Email'),
    ], string='Contact Method', required=True, default="email")
    apply_vector = fields.Char(
        string="Contact Point",
        help="The email address, phone number, url to send applications to.")
    post_html = fields.Html(string="Post", prefetch=False, required=True)
    status = fields.Selection([
        ('success', 'Success'),
        ('warning', 'Warning'),
        ('pending', 'Pending'),
        ('failure', 'Failure'),
        ('expired', 'Expired'),
        ('deleted', 'Deleted'),
    ], string='Status', required=True, readonly=True)
    status_message = fields.Text(
        string="Status Message", prefetch=False, readonly=True)
    api_data = fields.Json(string="API Data", prefetch=False, readonly=True)
    campaign_start_date = fields.Date(
        string="Campaign Start Date", default=fields.Date.today(),
        help='The date when the campaign will start.')
    campaign_end_date = fields.Date(
        string="Campaign End Date",
        help='The date when the campaign will end. If not set, '
        'the campaign will run indefinitely or to the maximum allowed by a platform.')
    company_id = fields.Many2one(related='job_id.company_id')

    def _compute_display_name(self):
        for record in self:
            record.display_name = _(
                '%(job)s on %(platform)s',
                job=record.job_id.name,
                platform=record.platform_id.name
            )

    def unlink(self):
        for job_post in self:
            job_post.sudo()._delete_post()
        return super().unlink()

    def _start_new_campaign(self):
        posts_to_start = self.env['hr.job.post'].search([
            ('status', '=', 'pending'),
            ('campaign_start_date', '<=', fields.Date.today()),
            '|',
                ('campaign_end_date', '>=', fields.Date.today()),
                ('campaign_end_date', '=', False),
        ], order='campaign_start_date', limit=5)
        wizards = self.env['hr.recruitment.post.job.wizard'].create([
            {
                'job_id': post.job_id.id,
                'apply_method': post.apply_method,
                'platform_ids': [(6, 0, post.platform_id.ids)],
                'campaign_start_date': post.campaign_start_date,
                'campaign_end_date': post.campaign_end_date,
                'post_html': post.post_html,
                'post_ids': post.ids,
                post._contact_point_to_vector(): post.apply_vector,
            } for post in posts_to_start
        ])
        for wizard in wizards:
            wizard._post_job()
        if len(posts_to_start) == 5:
            self.env.ref('hr_recruitment_integration_base.job_board_campaign_manager_start')._trigger()

    def _stop_finished_campaign(self):
        posts_to_end = self.env['hr.job.post'].search([
            ('status', 'not in', ['deleted', 'expired']),
            ('campaign_end_date', '<=', fields.Date.today()),
        ], order='campaign_end_date', limit=5)
        for post in posts_to_end:
            post._delete_post()
        if len(posts_to_end) == 5:
            self.env.ref('hr_recruitment_integration_base.job_board_campaign_manager_stop')._trigger()

    def _delete_post(self):
        """Delete the post on the platform.
        to be overridden by the specific platform module."""
        pass

    def _contact_point_to_vector(self):
        self.ensure_one()
        if self.apply_method == 'email':
            return 'job_apply_mail'
        return ''

    def action_update_job_post_check(self):
        self.ensure_one()
        if self.platform_id.price_to_update:
            raise RedirectWarning(
                message=_('This action will update the job post on the platform. '
                            'This action will cost %(price)s credits. Do you want to continue?',
                            price=self.platform_id.price_to_update),
                action=self.env.ref('hr_recruitment_integration_base.hr_job_post_double_check_action').id,
                additional_context={
                    'active_id': self.id,
                    'uid': self.env.user.id,
                },
                button_text=_('Update'),
            )
        self.action_update_job_post()

    def action_update_job_post(self):
        self.ensure_one()
        post_wizard = self.env['hr.recruitment.post.job.wizard'].create({
            'job_id': self.job_id.id,
            'apply_method': self.apply_method,
            'platform_ids': [(6, 0, self.platform_id.ids)],
            'campaign_start_date': self.campaign_start_date,
            'campaign_end_date': self.campaign_end_date,
            'post_html': self.post_html,
            'post_ids': self.ids,
            self._contact_point_to_vector(): self.apply_vector,
            'api_data': self.api_data,
        })
        post_wizard.action_post_job()
        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }

    def action_post_job(self):
        post_wizard = self.env['hr.recruitment.post.job.wizard'].create({
            'job_id': self.job_id.id,
            'apply_method': self.apply_method,
            'post_html': self.post_html,
        })

        return {
            'name': _('Reuse Job Post'),
            'type': 'ir.actions.act_window',
            'res_model': 'hr.recruitment.post.job.wizard',
            'res_id': post_wizard.id,
            'view_mode': 'form',
            'views': [(False, 'form')],
            'target': 'new',
        }

    def action_post_now(self):
        self.ensure_one()
        self.sudo().write({
            'campaign_start_date': fields.Date.today(),
        })
        self._start_new_campaign()

    def action_stop_campaign(self):
        self.ensure_one()
        self.sudo().write({
            'campaign_end_date': fields.Date.today(),
        })
        self._stop_finished_campaign()

    def create(self, values):
        posts = super().create(values)
        posts._log_post_modifications()
        return posts

    def _log_post_modifications(self, mode=None):
        if mode is None:
            mode = _('created')
        for post in self:
            post.message_post(
                author_id=self.env.user.partner_id.id,
                subject=_(
                    'Job Post on %(platform)s has been modified',
                    platform=post.platform_id.name
                ),
                body=Markup("""
                        <strong>%(line_1)s</strong> <br/>
                        <strong>%(line_2)s</strong>  %(job)s\n<br/>
                        <strong>%(line_3)s</strong>  %(status)s<br/>
                        <strong>%(line_4)s</strong> %(status_message)s<br/>
                        <strong>%(line_5)s</strong> %(method)s<br/>
                        <strong>%(line_6)s</strong> %(vector)s<br/>
                        <strong>%(line_7)s</strong> %(start_date)s<br/>
                        <strong>%(line_8)s</strong> %(end_date)s <br/>
                        <strong>%(line_9)s</strong> %(company)s
                    """ % {
                        'line_1': _("Job Post on %(platform)s has been %(mode)s", platform=post.platform_id.name, mode=mode),
                        'line_2': _("Job:"),
                        'line_3': _("Status:"),
                        'line_4': _("Status Message:"),
                        'line_5': _("Contact Method:"),
                        'line_6': _("Contact Point:"),
                        'line_7': _("Campaign Start Date:"),
                        'line_8': _("Campaign End Date:"),
                        'line_9': _("Company:"),
                        'job': post.job_id.name,
                        'status': dict(post._fields['status'].selection).get(post.status),
                        'status_message': post.status_message,
                        'method': dict(post._fields['apply_method'].selection).get(post.apply_method),
                        'vector': post.apply_vector,
                        'start_date': post.campaign_start_date,
                        'end_date': post.campaign_end_date or _('No Limit'),
                        'company': post.company_id.name,
                    }
                )
            )
