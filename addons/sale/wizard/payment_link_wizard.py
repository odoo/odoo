# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from werkzeug import urls

from odoo import api, fields, models
from odoo.exceptions import ValidationError
from odoo.addons.payment import utils as payment_utils


class PaymentLinkWizard(models.TransientModel):
    _inherit = 'payment.link.wizard'
    _description = 'Generate Sales Payment Link'

    confirm_order = fields.Boolean(
        help="This payment will confirm the order.",
        compute="_compute_confirm_order",
        inverse="_inverse_confirm_order"
    )
    amount_paid = fields.Monetary(
        currency_field='currency_id',
        help="Amount partially paid on this order.",
        string="Already Paid."
    )
    override_confirm = fields.Integer(compute="_compute_override_confirm")

    # This field inherits the state of the current sale order to decide if the order can be
    # confirmed or not (e.g. a cancelled order cannot be confirmed).
    order_state = fields.Selection([
        ('draft', 'Quotation'),
        ('sent', 'Quotation Sent'),
        ('sale', 'Sales Order'),
        ('done', 'Locked'),
        ('cancel', 'Cancelled'),
    ],
        default='draft',
        help="Inherits the state of the SO from which this payment link is derived."
    )

    @api.model
    def default_get(self, fields):
        res = super().default_get(fields)
        if res['res_id'] and res['res_model'] == 'sale.order':
            record = self.env[res['res_model']].browse(res['res_id'])
            res.update({
                'description': record.name,
                'amount': (record.amount_total
                           - sum(record.invoice_ids.filtered(lambda x: x.state != 'cancel')
                                 .mapped('amount_total'))
                           - record.amount_paid()),
                'amount_paid': record.amount_paid(),
                'currency_id': record.currency_id.id,
                'partner_id': record.partner_id.id,
                'amount_max': record.amount_total,
                'order_state': record.state,
            })
        return res

    @api.depends('amount')
    def _compute_override_confirm(self):
        for payment_link in self:
            payment_link.override_confirm = payment_link.currency_id.compare_amounts(
                payment_link.amount_max - payment_link.amount_paid, payment_link.amount)

    @api.onchange('amount')
    def _onchange_amount(self):
        for payment_link in self:
            amount_to_be_paid = payment_link.amount_max - payment_link.amount_paid
            if payment_link.amount > amount_to_be_paid:
                raise ValidationError(
                    f"Please set an amount smaller than {amount_to_be_paid}."
                )

    @api.depends('amount')
    def _compute_confirm_order(self):
        for payment_link in self:
            payment_link.confirm_order = (
                    payment_link.amount == payment_link.amount_max - payment_link.amount_paid
            )

    def _inverse_confirm_order(self):
        for payment_link in self:
            payment_link.amount = (
                payment_link.amount
                if payment_link.amount else payment_link.amount_to_be_paid
            )

    @api.depends('amount', 'description', 'partner_id', 'currency_id', 'payment_acquirer_selection',
                 'confirm_order')
    def _compute_values(self):
        for payment_link in self:
            if payment_link.res_model != 'sale.order':
                super()._compute_values()
            else:
                payment_link.access_token = payment_utils.generate_access_token(
                    payment_link.partner_id.id, payment_link.amount, payment_link.currency_id.id,
                    payment_link.confirm_order
                )
        # must be called after token generation, obvsly - the link needs an up-to-date token
        self._generate_link()

    def _get_payment_acquirer_available(self, res_model, res_id, **kwargs):
        """ Select and return the acquirers matching the criteria.

        :param str res_model: active model
        :param int res_id: id of 'active_model' record
        :return: The compatible acquirers
        :rtype: recordset of `payment.acquirer`
        """
        if res_model == 'sale.order':
            kwargs['sale_order_id'] = res_id
        return super()._get_payment_acquirer_available(**kwargs)

    def _generate_link(self):
        """ Override of payment to add the sale_order_id in the link. """
        for payment_link in self:
            # The sale_order_id field only makes sense if the document is a sales order
            if payment_link.res_model == 'sale.order':
                related_document = self.env[payment_link.res_model].browse(payment_link.res_id)
                base_url = related_document.get_base_url()
                payment_link.link = f'{base_url}/payment/pay' \
                                    f'?reference={urls.url_quote(payment_link.description)}' \
                                    f'&amount={payment_link.amount}' \
                                    f'&sale_order_id={payment_link.res_id}' \
                                    f'{"&acquirer_id=" + str(payment_link.payment_acquirer_selection) if payment_link.payment_acquirer_selection != "all" else "" }' \
                                    f'&confirm_order={payment_link.confirm_order}'\
                                    f'&access_token={payment_link.access_token}'
                # Order-related fields are retrieved in the controller
            else:
                super(PaymentLinkWizard, payment_link)._generate_link()
