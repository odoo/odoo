# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.osv.expression import AND


class HrReferralCampaignWizard(models.TransientModel):
    _name = 'hr.referral.campaign.wizard'
    _description = 'Referral Campaign Wizard'

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        if self.env.context.get('active_model') == 'hr.job':
            res['job_id'] = self.env.context.get('active_id')
        return res

    def _domain_employee_ids(self):
        return [('user_id', '!=', False), ('company_id', 'in', self.env.companies.ids)]

    job_id = fields.Many2one('hr.job', string='Job Position', readonly=True, required=True)
    is_published = fields.Boolean(related='job_id.is_published', export_string_translation=False)
    target = fields.Selection(
        selection=[('all', 'All'), ('selection', 'Selection')],
        string='Contacted Employees', default='all', required=True)
    employee_ids = fields.Many2many(
        comodel_name='hr.employee', domain=_domain_employee_ids, store=True, export_string_translation=False)
    sending_method = fields.Selection(
        selection=[('work_email', 'Email'), ('work_phone', 'SMS')], default='work_email', required=True)

    mail_subject = fields.Char(string='Subject', compute='_compute_mail_subject', readonly=False, store=True)
    mail_body = fields.Html(string='Body', compute='_compute_mail_body', readonly=False, store=True)

    sms_body = fields.Text(string='SMS Content', compute='_compute_sms_body', readonly=False, store=True)

    @api.depends('job_id')
    def _compute_sms_body(self):
        for wizard in self:
            if not wizard.sms_body:
                wizard.sms_body = self.env['ir.ui.view']._render_template(
                    'hr_referral.referral_campaign_sms_template',
                    {
                        'employee_name': '[employee_name]',
                        'job_id': wizard.job_id,
                        'company_id': wizard.job_id.company_id,
                        'job_url': '[job_url]',
                    }
                )

    @api.depends('job_id')
    def _compute_mail_body(self):
        for wizard in self:
            if not wizard.mail_body:
                wizard.mail_body = self.env['ir.ui.view']._render_template(
                    'hr_referral.referral_campaign_email_body_template',
                    {
                        'employee_name': '[employee_name]',
                        'job_id': wizard.job_id,
                        'company_id': wizard.job_id.company_id,
                        'job_url': '[job_url]',
                    }
                )

    @api.depends('job_id')
    def _compute_mail_subject(self):
        for wizard in self:
            if not wizard.mail_subject:
                wizard.mail_subject = _(
                    'Job Offer for a %(job_title)s at %(company_name)s',
                    company_name=wizard.job_id.company_id.name,
                    job_title=wizard.job_id.name,
                )

    def _get_employees(self):
        self.ensure_one()
        if self.target == 'selection':
            return self.employee_ids.filtered(lambda employee: employee[self.sending_method])
        base_domain = [('company_id', 'in', self.env.companies.ids), ('user_id', '!=', False)]
        sending_domain = []
        if self.sending_method == 'work_phone':
            sending_domain = ['|', ('work_phone', '!=', False), ('user_id.work_phone', '!=', False)]
        search_domain = AND([base_domain, sending_domain])
        return self.env['hr.employee'].search(search_domain)

    def _prepare_personalized_content(self):
        self.ensure_one()
        users = self._get_employees().user_id

        if not users:
            raise UserError(_('No users to send the campaign to. Please adapt your target.'))
        if not self.is_published:
            self.job_id.write({'is_published': True})

        links_per_user = self.job_id.search_or_create_referral_links(users)
        sending_method = 'email_formatted' if self.sending_method == 'work_email' else 'work_phone'
        personalized_contents = [{
            'employee_name': user.employee_id.name,
            'sending_method': user[sending_method]
                # if the sending vector != mail, the field is not required on the user
                or next(employee[sending_method] for employee in user.employee_ids if employee[sending_method]),
            'job_url': links_per_user[user],
        } for user in users]
        return personalized_contents

    def _action_send_email(self):
        personalized_contents = self._prepare_personalized_content()
        mails = [{
            'email_to': personalized_content['sending_method'],
            'email_from': self.env.user.email_formatted,
            'author_id': self.env.user.partner_id.id,
            'auto_delete': True,
            'subject': self.mail_subject,
            'body_html': self.mail_body
                .replace('[employee_name]', personalized_content['employee_name'])
                .replace('[job_url]', personalized_content['job_url'])
                .replace('%5Bjob_url%5D', personalized_content['job_url']),
            'model': None,
            'res_id': None,
        } for personalized_content in personalized_contents]
        self.env['mail.mail'].sudo().create(mails)
        return {'type': 'ir.actions.act_window_close'}

    def _action_send_sms(self):
        personalized_contents = self._prepare_personalized_content()
        smss = [{
            'number': personalized_content['sending_method'],
            'body': self.sms_body
                .replace('[employee_name]', personalized_content['employee_name'])
                .replace('[job_url]', personalized_content['job_url']),
        } for personalized_content in personalized_contents]
        self.env['sms.sms'].sudo().create(smss)
        return {'type': 'ir.actions.act_window_close'}

    def action_send(self):
        self.ensure_one()
        if self.sending_method == 'work_email':
            return self._action_send_email()
        return self._action_send_sms()
