# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models


class MailThread(models.AbstractModel):
    """ Update MailThread to add the support of bounce management for crm.lead. """
    _inherit = 'mail.thread'

    def _message_reset_bounce(self, email_from):
        """Includes leads in reset bounce process."""
        super(MailThread, self)._message_reset_bounce(email_from)
        if email_from:
            for lead in self.env['crm.lead']._get_records_from_email(email_from):
                lead.message_bounce = 0
