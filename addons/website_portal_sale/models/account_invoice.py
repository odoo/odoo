# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, exceptions, models


class AccountInvoice(models.Model):
    _inherit = 'account.invoice'

    @api.multi
    def _notification_recipients(self, message, groups):
        groups = super(AccountInvoice, self)._notification_recipients(message, groups)

        for group_name, group_method, group_data in groups:
            group_data['has_button_access'] = True

        return groups

    @api.multi
    def get_access_action(self):
        """ Instead of the classic form view, redirect to the online invoice for portal users. """
        self.ensure_one()
        if self.env.user.share or self.env.context.get('force_website'):
            try:
                self.check_access_rule('read')
            except exceptions.AccessError:
                pass
            else:
                return {
                    'type': 'ir.actions.act_url',
                    'url': '/my/invoices',  # No controller /my/invoices/<int>, only a report pdf
                    'target': 'self',
                    'res_id': self.id,
                }
        return super(AccountInvoice, self).get_access_action()

    @api.multi
    def get_signup_url(self):
        self.ensure_one()
        return self.partner_id.with_context(signup_valid=True)._get_signup_url_for_action(
            action='/mail/view',
            model=self._name,
            res_id=self.id)[self.partner_id.id]
