# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.


from odoo import _, fields, models


class HrReferralAlertMailWizard(models.TransientModel):
    _name = 'hr.referral.alert.mail.wizard'
    _description = 'Referral Alert Mail Wizard'
    _rec_name = 'subject'

    def _get_user_domain(self):
        return [('share', '=', False), ('company_ids', 'in', self.env.company.id),
            ('groups_id', 'in', self.env.ref('hr_referral.group_hr_recruitment_referral_user').id)]

    def _default_user_ids(self):
        user_ids = self.env['res.users'].search(self._get_user_domain())
        return [(6, 0, user_ids.ids)]

    def _default_body(self):
        url = '/odoo/action-hr_referral.action_hr_referral_welcome_screen'
        return _('A new alert has been added to the Referrals app! Check your <a href=%(url)s>dashboard</a> now!', url=url)

    user_ids = fields.Many2many('res.users', 'Users', domain=_get_user_domain, default=_default_user_ids, store=False)
    subject = fields.Char(required=True, default=lambda self: _('New Alert In Referrals App'))
    body = fields.Html(required=True, default=_default_body)

    def action_send(self):
        self.ensure_one()
        self.env['mail.thread'].message_notify(
            partner_ids=self.user_ids.partner_id.ids,
            model_description='Referral Alerts',
            subject=self.subject,
            body=self.body,
            email_layout_xmlid='mail.mail_notification_light',
        )
        return True
