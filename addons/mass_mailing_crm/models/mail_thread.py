# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models


class MailThread(models.AbstractModel):
    """ Update MailThread to add the support of bounce management for crm.lead. """
    _inherit = 'mail.thread'

    def _reset_message_bounce(self, email_from):
        """Called by ``message_process`` when a new mail is received from an email address.
        If the email is related to a lead, we consider that the number of message_bounce
        is not relevant anymore as the email is valid - as we received an email from this
        address

        :param email_from: email address that sent the incoming email."""
        super(MailThread, self)._reset_message_bounce(email_from)
        if email_from:
            partners = self._get_records_from_email('crm.lead', email_from)
            for partner in partners:
                partner.message_bounce = 1
