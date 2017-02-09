# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import datetime

from odoo import api, fields, models

class MailComposeMessage(models.TransientModel):
    _inherit = 'mail.compose.message'

    @api.multi
    def send_mail(self, auto_commit=False):
        context = self._context
        # TODO TDE: clean that brole one day
        if self.model == 'sale.order':
            self.env['sale.order'].search([
                ('id', 'in', context.get('active_ids')),
                ('cart_recovery_email_sent', '!=', True),
                ('is_abandoned_cart', '=', True)
            ]).write({'cart_recovery_email_sent': True})
            self = self.with_context(mail_post_autofollow=True)
        return super(MailComposeMessage, self).send_mail(auto_commit=auto_commit)
