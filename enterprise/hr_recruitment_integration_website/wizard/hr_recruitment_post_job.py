# Part of Odoo. See LICENSE file for full copyright and licensing details.


from odoo import fields, models, _
from odoo.exceptions import UserError, RedirectWarning


class HrRecruitmentPostJobWizard(models.TransientModel):
    _inherit = 'hr.recruitment.post.job.wizard'

    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        job = self.env['hr.job'].browse(res.get('job_id'))
        if 'job_apply_url' in fields_list:
            res['job_apply_url'] = job.full_url
        if 'post_html' in fields_list:
            res['post_html'] = job._get_plain_text_description()
        return res

    apply_method = fields.Selection(
        selection_add=[
            ('redirect', 'Redirect to company\'s website'),
        ], default='redirect')
    job_apply_url = fields.Char('Job url')
    # required are dropped to permit the user to generate the post without filling the fields
    post_html = fields.Html(required=False)
    platform_ids = fields.Many2many(required=False)
    campaign_start_date = fields.Date(required=False)

    def _get_apply_vector(self):
        self.ensure_one()
        if self.apply_method == 'redirect':
            return self.job_apply_url
        return super()._get_apply_vector()

    def action_post_job(self):
        self.ensure_one()
        if not self.platform_ids:
            raise UserError(_('At least one platform must be selected'))
        if self.apply_method == 'redirect' and not self.job_apply_url:
            raise UserError(_('URL is required if the apply method is \'Redirect to company\'s website\'.'))
        if not self.post_html:
            raise UserError(_('Post is required.'))
        if not self.campaign_start_date:
            raise UserError(_('Campaign Start Date is required.'))
        if self.apply_method == 'redirect' and not self.job_id.is_published:
            raise UserError(_(
                'The job must be published on the website to generate a post with a redirect apply method.'
            ))
        return super().action_post_job()

    def action_generate_post(self, warning=True):
        self.ensure_one()
        if self.post_html and warning:
            raise RedirectWarning(
                message=_('The Job Description will be replaced with the generated one, do you want to continue?'),
                action=self.env.ref(
                    'hr_recruitment_integration_website.hr_recruitment_post_job_wizard_action_regenerate_post').id,
                button_text=_('Generate'),
                additional_context={'active_id': self.id}
            )
        self.post_html = self.job_id._generate_post()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Post Job'),
            'res_model': self._name,
            'view_mode': 'form',
            'res_id': self.id,
            'views': [(False, 'form')],
            'context': {'active_model': self._name},
            'target': 'new',
        }
