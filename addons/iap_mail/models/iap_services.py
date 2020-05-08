# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, exceptions, models, _


class IapServices(models.AbstractModel):
    _inherit = 'iap.services'

    # ------------------------------------------------------------
    # MAIL HELPERS AND TOOLS
    # ------------------------------------------------------------

    @api.model
    def _iap_notify_nocredit(self, service_name, model_name, notification_parameter=None):
        """ Notify about missing creadits. An optional notification parameter can be used
        to avoid spamming people. """
        iap_account = self._iap_get_service_account(service_name, force_create=False)
        if not iap_account:
            return False

        if notification_parameter:
            already_notified = self.env['ir.config_parameter'].sudo().get_param(notification_parameter, False)
            if already_notified:
                return False

        mail_template = self.env.ref('iap_mail.mail_template_iap_service_no_credits', raise_if_not_found=False)
        if not mail_template:
            return False

        # Get the email address of the creators of the records
        res = self.env[model_name].search_read([], ['create_uid'], limit=100)
        uids = set(r['create_uid'][0] for r in res if r.get('create_uid'))
        res = self.env['res.users'].search_read([('id', 'in', list(uids))], ['email'])
        emails = set(r['email'] for r in res if r.get('email'))

        email_values = {
            'email_to': ','.join(emails)
        }
        mail_template.send_mail(iap_account.id, force_send=True, email_values=email_values)

        if notification_parameter:
            self.env['ir.config_parameter'].sudo().set_param(notification_parameter, True)
        return True
