# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class MailComposeMessage(models.TransientModel):
    _inherit = 'mail.compose.message'

    def send_mail(self, **kwargs):
        for wizard in self:
            if self._context.get('mark_coupon_as_sent') and wizard.model == 'coupon.coupon' and wizard.partner_ids:
                # Mark coupon as sent in sudo, as helpdesk users don't have the right to write on coupons
                self.env[wizard.model].sudo().browse(wizard.res_id).state = 'sent'
        return super().send_mail(**kwargs)
