# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, exceptions, models
from werkzeug.urls import url_encode


class AccountInvoice(models.Model):
    _inherit = 'account.invoice'

    @api.multi
    def _notification_recipients(self, message, groups):
        groups = super(AccountInvoice, self)._notification_recipients(message, groups)

        for group_name, group_method, group_data in groups:
            group_data['has_button_access'] = True

        return groups

    def get_mail_url(self):
        self.ensure_one()
        params = {
            'model': self._name,
            'res_id': self.id,
        }
        params.update(self.partner_id.signup_get_auth_param()[self.partner_id.id])
        return '/mail/view?' + url_encode(params)

    @api.multi
    def get_signup_url(self):
        self.ensure_one()
        return self.partner_id.with_context(signup_valid=True)._get_signup_url_for_action(
            action='/mail/view',
            model=self._name,
            res_id=self.id)[self.partner_id.id]
