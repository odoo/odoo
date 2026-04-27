# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import AccessError


class HrReferralSendMail(models.TransientModel):
    _name = 'hr.referral.send.mail'
    _description = 'Referral Send Mail'

    job_id = fields.Many2one(
        'hr.job', readonly=True,
        default=lambda self: self.env.context.get('active_id', None),
    )
    url = fields.Char(compute='_compute_url', readonly=True)
    email_to = fields.Char(string="Email", required=True)
    subject = fields.Char('Subject', default="Job for you")
    body_html = fields.Html('Body', compute='_compute_body_html', store=True, readonly=False)

    @api.depends('job_id')
    def _compute_url(self):
        link_wizards = self.env['hr.referral.link.to.share'].create([{
            'job_id': wizard.job_id.id,
            'channel': 'direct',
        } for wizard in self])
        for wizard, link_wizard in zip(self, link_wizards):
            wizard.url = link_wizard.url

    @api.depends('job_id', 'url')
    def _compute_body_html(self):
        for wizard in self:
            wizard.body_html = self.env["ir.ui.view"]._render_template(
                'hr_referral.referral_email_body_template',
                {
                    'job_id': wizard.job_id,
                    'companies': self.env.companies.filtered(lambda c: c.website_id.domain or c.website),
                    'url': wizard.url,
                }
            )

    def send_mail_referral(self):
        if not self.env.user.has_group('hr_referral.group_hr_recruitment_referral_user'):
            raise AccessError(_("Do not have access"))

        self.env['mail.mail'].sudo().create({
            'body_html': self.body_html,
            'author_id': self.env.user.partner_id.id,
            'email_from': self.env.user.email_formatted,
            'email_to': self.email_to,
            'subject': self.subject
        }).send()

        return {'type': 'ir.actions.act_window_close'}
