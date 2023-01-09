# -*- coding: utf-8 -*-
# purches Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class MailComposeMessage(models.TransientModel):
    _inherit = 'mail.compose.message'

    def _action_send_mail(self, auto_commit=False):
        if self.model == 'purchase.order':
            self = self.with_context(mailing_document_based=True)
        return super(MailComposeMessage, self)._action_send_mail(auto_commit=auto_commit)
