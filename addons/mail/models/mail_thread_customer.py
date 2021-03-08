# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, exceptions, models, tools, _
from odoo.osv import expression


class MailThreadCustomer(models.AbstractModel):
    _name = 'mail.thread.customer'
    _inherit = 'mail.thread'
    _description = 'Thread Customer Management'
    # override those parameters with actual fields used in model
    _mail_field_email = 'email'
    _mail_field_customer = 'partner_id'

    @api.model
    def message_new(self, msg_dict, custom_values=None):
        if 'user_id' in self:
            self_ctx = self.with_context(default_user_id=False)

        customer_id = msg_dict.get('author_id')
        customer = self.env['res.partner'].browse([customer_id]) if customer_id else self.env['res.partner']
        customer_email = msg_dict.get('email_from') or customer.email

        defaults = dict({
            self._mail_field_email: customer_email,
            self._mail_field_customer: customer.id,
        }, **(custom_values or {}))
        return super(MailThreadCustomer, self_ctx).message_new(msg_dict, custom_values=defaults)

    # ----------------------------------------------------------------------
    # CRUD
    # ----------------------------------------------------------------------

    @api.model_create_multi
    def create(self, vals_list):
        """ Override to subscribe (non public) customers to record and synchronize
        email if not set. """
        records = super(MailThreadCustomer, self).create(vals_list)

        for record in records:
            customer = record[self._mail_field_customer]
            if customer and not customer.partner_public:
                record.message_subscribe(customer.ids)
                if not record[self._mail_field_email] and customer.email:
                    record[self._mail_field_email] = customer.email
        return records

    def write(self, vals):
        """ Override to subscribe (non public) customers to record and synchronize
        email if not set. """
        res = super(MailThreadCustomer, self).write(vals)

        if vals.get(self._mail_field_customer):
            for record in self:
                customer = record[self._mail_field_customer]
                if customer and not customer.partner_public:
                    record.message_subscribe(customer.ids)
                    if not record[self._mail_field_email] and customer.email:
                        record[self._mail_field_email] = customer.email

        return res

    # ----------------------------------------------------------------------
    # POST API
    # ----------------------------------------------------------------------

    @api.returns('mail.message', lambda value: value.id)
    def message_post(self, **kwargs):
        """ Subscribe customer if not public and if targeted in message as a direct
        recipient to ensure he receives all future answers. """
        self.ensure_one()
        message = super(MailThreadCustomer, self).message_post(**kwargs)

        customer = self[self._mail_field_customer]
        if customer and customer in message.partner_ids and not customer.partner_public:
            self.message_subscribe(self[self._mail_field_customer].ids)

        return message

    def _message_post_after_hook(self, message, msg_vals):
        """ If current document has a customer email but still no customer
        we try to set customer after a message post that has some specific
        recipients (aka ``partner_ids``, not followers). If a recipient uses
        this email it was probably created after creating this record. This
        is the case when unknown email create documents and replying to it
        creates a partner through chatter tools for example.

        This is done in backend independently from what JS / Chatter could do
        to ensure document is updated whatever user flow and whatever the state
        of Discuss features. """
        self.ensure_one()
        if self[self._mail_field_email] and not self[self._mail_field_customer]:
            email_from = self[self._mail_field_email]
            email_from_normalized = tools.email_normalize(email_from)
            new_partner = message.partner_ids.filtered(
                lambda partner: partner.email == email_from or partner.email_normalized == email_from_normalized
            )
            if new_partner:
                domain = self._message_post_update_customer_filter()
                if hasattr(self, 'email_normalized'):
                    domain = expression.AND([
                        domain,
                        [('email_normalized', '=', new_partner.email_normalized)],
                    ])
                else:
                    # due to possible formation of email field, we are not sure to catch
                    # all similar emails; using ilike may lead to false positives (john.doe@example.com
                    # when searching doe@example.com).
                    domain = expression.AND([
                        domain,
                        [(self._mail_field_email, 'in',
                          [new_partner.email, new_partner.email_normalized,
                           email_from, email_from_normalized]
                         )
                        ],
                    ])
                self.search(domain).write({self._mail_field_customer: new_partner.id})
        return super(MailThreadCustomer, self)._message_post_after_hook(message, msg_vals)

    def _message_post_update_customer_filter(self):
        return [(self._mail_field_customer, '=', False)]

    # ----------------------------------------------------------------------
    # RECIPIENTS
    # ----------------------------------------------------------------------

    def _message_get_suggested_recipients(self):
        recipients = super(MailThreadCustomer, self)._message_get_suggested_recipients()
        try:
            for record in self:
                if record[self._mail_field_customer] and not record[self._mail_field_customer].partner_public:
                    record._message_add_suggested_recipient(
                        recipients,
                        partner=record[self._mail_field_customer],
                        reason=_('Customer')
                    )
                elif record[self._mail_field_email]:
                    record._message_add_suggested_recipient(
                        recipients,
                        email=record[self._mail_field_email],
                        reason=_('Customer Email')
                    )
        except exceptions.AccessError:  # no read access rights -> just ignore suggested recipients because this imply modifying followers
            pass
        return recipients
