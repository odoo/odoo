# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import AccessError


class HrReferralSendSMS(models.TransientModel):
    _name = 'hr.referral.send.sms'
    _description = 'Referral Send sms'

    job_id = fields.Many2one(
        'hr.job', readonly=True,
        default=lambda self: self.env.context.get('active_id', None),
    )
    url = fields.Char(compute='_compute_url', readonly=True)
    recipient = fields.Char(string="Recipient", required=True)
    body_plaintext = fields.Text(
        string="Body", compute='_compute_body_plaintext',
        required=True, readonly=False
    )

    @api.depends('job_id')
    def _compute_url(self):
        link_wizards = self.env['hr.referral.link.to.share'].create([{
            'job_id': wizard.job_id.id,
            'channel': 'direct',
        } for wizard in self])
        for wizard, link_wizard in zip(self, link_wizards):
            wizard.url = link_wizard.url

    @api.depends('job_id', 'url')
    def _compute_body_plaintext(self):
        for wizard in self:
            if not wizard.body_plaintext:
                wizard.body_plaintext = _(
                    'Hello! There is an amazing job offer for %(job_name)s in my company!'
                    ' It will be a fit for you %(referral_url)s',
                    job_name=wizard.job_id.name,
                    referral_url=wizard.url,
                )

    def send_sms_referral(self):
        if not self.env.user.has_group('hr_referral.group_hr_recruitment_referral_user'):
            raise AccessError(_('You do not have the required access rights to send SMS.'))

        self.env['sms.sms'].create([{
            'number': wizard.recipient,
            'body': wizard.body_plaintext,
        } for wizard in self]).send()

        return {'type': 'ir.actions.act_window_close'}
