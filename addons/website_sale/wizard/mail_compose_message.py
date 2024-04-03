# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models


class MailComposeMessage(models.TransientModel):
    _inherit = 'mail.compose.message'

    def _action_send_mail(self, auto_commit=False):
        context = self._context
        # Task-2792146: will move to model-based method
        if context.get('website_sale_send_recovery_email') and self.model == 'sale.order' and context.get('active_ids'):
            self.env['sale.order'].search([
                ('id', 'in', context.get('active_ids')),
                ('cart_recovery_email_sent', '=', False),
                ('is_abandoned_cart', '=', True)
            ]).write({'cart_recovery_email_sent': True})
        return super(MailComposeMessage, self)._action_send_mail(auto_commit=auto_commit)
