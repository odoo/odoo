# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models


class MailMail(models.Model):
    _name = 'mail.mail'
    _inherit = 'mail.mail'

    @api.multi
    def _postprocess_sent_message(self, mail_sent=True):
        for mail in self:
            if mail_sent and mail.model == 'purchase.order':
                purchase_order = self.env['purchase.order'].browse(mail.res_id)
                if purchase_order.state == 'draft':
                    self.env['purchase.order'].signal_workflow([mail.res_id], 'send_rfq')
        return super(MailMail, self)._postprocess_sent_message(mail_sent=mail_sent)
