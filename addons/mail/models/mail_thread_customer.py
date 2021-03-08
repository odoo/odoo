# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, api, fields, models, tools


class MailThreadCustomer(models.AbstractModel):
    _name = 'mail.thread.customer'
    _inherit = 'mail.thread'
    _description = 'Thread Customer Management'
    # override those parameters with actual fields used in model
    _field_email = 'email'
    _field_customer = 'partner_id'

    @api.model
    def message_new(self, msg_dict, custom_values=None):
        if 'user_id' in self:
            self = self.with_context(default_user_id=False)

        author_identity_id = msg_dict.get('author_identity_id')
        author_identity = self.env['mail.identity'].browse(author_identity_id) if author_identity_id else self.env['mail.identity']
        customer = author_identity.partner_id

        defaults = dict({
            self._field_email: msg_dict.get('email_from'),
            self._field_customer: customer.id,
        }, **(custom_values or {}))
        thread = super(MailThreadCustomer, self).message_new(msg_dict, custom_values=defaults)

        if customer:
            thread.message_subscribe(partner_ids=customer.ids)

        return thread
