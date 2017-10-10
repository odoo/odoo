# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging

from odoo import models, _

from odoo.addons.iap.models.iap import InsufficientCreditError

_logger = logging.getLogger(__name__)


class MailThread(models.AbstractModel):
    _inherit = 'mail.thread'

    def _get_default_sms_recipients(self):
        """ This method will likely need to be overriden by inherited models.
               :returns partners: recordset of res.partner
        """
        partners = self.env['res.partner']
        if hasattr(self, 'partner_id'):
            partners |= self.mapped('partner_id')
        if hasattr(self, 'partner_ids'):
            partners |= self.mapped('partner_ids')
        return partners

    def message_post_send_sms(self, sms_message, numbers=None, partners=None, note_msg=None, log_error=False):
        """ Send an SMS text message and post an internal note in the chatter if successfull
            :param sms_message: plaintext message to send by sms
            :param partners: the numbers to send to, if none are given it will take those
                                from partners or _get_default_sms_recipients
            :param partners: the recipients partners, if none are given it will take those
                                from _get_default_sms_recipients, this argument
                                is ignored if numbers is defined
            :param note_msg: message to log in the chatter, if none is given a default one
                             containing the sms_message is logged
        """
        if not numbers:
            if not partners:
                partners = self._get_default_sms_recipients()

                # Collect numbers, we will consider the message to be sent if at least one number can be found
                numbers = list(set([i.mobile for i in partners if i.mobile]))

        if numbers:
            try:
                self.env['sms.api']._send_sms(numbers, sms_message)
                mail_message = note_msg or _('SMS message sent: %s') % sms_message

            except InsufficientCreditError as e:
                if not log_error:
                    raise e
                mail_message = _('Insufficient credit, unable to send SMS message: %s') % sms_message
        else:
            mail_message = _('No mobile number defined, unable to send SMS message: %s') % sms_message

        for thread in self:
            thread.message_post(body=mail_message)
        return False
