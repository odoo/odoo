# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models


class Mail(models.Model):
    _inherit = 'mail.mail'

    @api.multi
    def _postprocess_sent_message(self, mail_sent=True):
        for mail in self:
            if mail_sent and mail.model == 'sale.order':
                order = self.env['sale.order'].browse(mail.res_id)
                partner = order.partner_id
                # Add the customer in the SO as follower
                if partner not in order.message_partner_ids:
                    order.message_subscribe([partner.id])
                # Add all recipients of the email as followers
                for partner in mail.partner_ids:
                    if partner not in order.message_partner_ids:
                        order.message_subscribe([partner.id])
        return super(Mail, self)._postprocess_sent_message(mail_sent=mail_sent)
