# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models
from odoo.exceptions import ValidationError
from odoo.fields import Domain

from odoo.addons.l10n_ph_qrph_maya import const

# Maya keeps a dynamic QRPH code valid for one hour. This is how long the kiosk waits before asking
# the customer what they want to do, not the moment the code on screen stops being payable.
KIOSK_QRPH_TIMEOUT = 180


class PosPaymentMethod(models.Model):
    _inherit = 'pos.payment.method'

    def _l10n_ph_is_kiosk_qrph(self):
        self.ensure_one()
        return self.payment_method_type == 'bank_qr_code' and self.qr_code_method == const.QR_METHOD

    @api.model
    def _load_pos_data_fields(self, config):
        # The kiosk decides on which methods it mints a QRPH code for, so it needs the method.
        return super()._load_pos_data_fields(config) + ['qr_code_method']

    @api.model
    def _load_pos_self_data_domain(self, data):
        # A bank QR code method is paid without a payment provider, so the kiosk domain of cash or
        # provider leaves it out: put the QRPH one back, the kiosk knows how to show its code.
        domain = super()._load_pos_self_data_domain(data)
        config = data['pos.config']
        if config.self_ordering_mode != 'kiosk':
            return domain
        qrph_domain = Domain.AND([
            Domain('id', 'in', config.payment_method_ids.ids),
            Domain('payment_method_type', '=', 'bank_qr_code'),
            Domain('qr_code_method', '=', const.QR_METHOD),
        ])
        return Domain.OR([qrph_domain, domain])

    @api.model
    def _allowed_actions_in_self_order(self):
        return super()._allowed_actions_in_self_order() + [
            'l10n_ph_kiosk_qrph_create_payment',
            'l10n_ph_kiosk_qrph_verify_payment',
        ]

    def l10n_ph_kiosk_qrph_create_payment(self, order_uuid):
        """ Give the kiosk the QRPH code to display, unless the order turns out to be paid already.

        :param str order_uuid: uuid of the <pos.order> the kiosk is collecting
        :return: ``{'qr_content': str, 'expires_in': int, 'short_payment': dict | None}``, or
            ``{'paid': True}`` when a code handed out earlier was paid after all
        :rtype: dict
        """
        self.ensure_one()
        order = self._l10n_ph_kiosk_qrph_get_order(order_uuid)

        # A code the kiosk stopped waiting for is still payable on Maya, so a customer who scanned
        # one just as the countdown ran out has really paid: settle that rather than charge twice.
        if self._l10n_ph_kiosk_qrph_settle_if_paid(order):
            return {'paid': True}

        bank = self.journal_id.bank_account_id.sudo()
        for error in (
            bank._get_error_messages_for_qr(const.QR_METHOD, order.partner_id, order.currency_id),
            bank._check_for_qr_code_errors(
                const.QR_METHOD, order.amount_total, order.currency_id, order.partner_id, order.name, ''),
        ):
            if error:
                raise ValidationError(error)

        # Minting is asked for the order rather than for the kiosk, so that the payment it opens on
        # Maya is the one that settles it. Within the reuse window this hands back the code
        # already on screen, which keeps a customer tapping retry from opening a second payment.
        qr_content = bank.with_context(
            l10n_ph_qrph_model='pos.order',
            l10n_ph_qrph_model_uuid=order.uuid,
            l10n_ph_qrph_company_id=order.company_id.id,
        )._get_qr_vals(const.QR_METHOD, order.amount_total, order.currency_id, order.partner_id, order.name, '')

        return {
            'qr_content': qr_content,
            'expires_in': KIOSK_QRPH_TIMEOUT,
            'short_payment': self._l10n_ph_kiosk_qrph_get_short_payment(order),
        }

    def l10n_ph_kiosk_qrph_verify_payment(self, order_uuid):
        """ Ask Maya about the codes issued for an order, for a customer who says they have paid.

        :param str order_uuid: uuid of the <pos.order> the kiosk is collecting
        :rtype: dict
        """
        self.ensure_one()
        order = self._l10n_ph_kiosk_qrph_get_order(order_uuid)
        paid = self._l10n_ph_kiosk_qrph_settle_if_paid(order)
        return {
            'paid': paid,
            'short_payment': None if paid else self._l10n_ph_kiosk_qrph_get_short_payment(order),
        }

    def _l10n_ph_kiosk_qrph_get_short_payment(self, order):
        """ Return the amounts to show when the customer paid less than their order costs.

        Example: the kiosk shows a QR code for 100, the customer adds an item (the order is now
        150) and then pays the QR code. Maya received 100, which does not settle the order. The
        kiosk tells the customer to see the merchant instead of "payment not received".

        :param order: the unpaid <pos.order> being collected
        :return: ``{'received': str, 'total': str}`` formatted for display, or ``None``
        :rtype: dict | None
        """
        self.ensure_one()
        transactions = self.env['l10n_ph.qrph.transaction'].search([
            ('pos_order_uuid', '=', order.uuid),
            ('state', '=', 'paid'),
            ('settled_date', '=', False),
        ])
        if not transactions:
            return None
        currency = order.currency_id
        return {
            'received': currency.format(sum(transactions.mapped('amount'))),
            'total': currency.format(order.amount_total),
        }

    def _l10n_ph_kiosk_qrph_settle_if_paid(self, order):
        """ Register the payment of an order if any code minted for it was paid.

        Every code handed out for the order is looked at, not only the one on screen: Maya has no
        way of taking a code back, so an earlier one the kiosk gave up on can still be what paid.
        One minted before the customer went back and added to their order no longer buys it,
        though, so what settles is a code covering what the order costs now.

        :param order: the <pos.order> being collected
        :return: whether the order came out of this paid
        :rtype: bool
        """
        self.ensure_one()
        transactions = self.env['l10n_ph.qrph.transaction'].search([
            ('pos_order_uuid', '=', order.uuid),
        ])
        if transaction := transactions._get_paid_transaction(order.amount_total):
            if order._l10n_ph_qrph_settle_kiosk_payment(self, transaction):
                # The kiosk is waiting on the bus for the order to be paid, to show its receipt.
                order._send_payment_result('Success')
        # The order may have been settled by an earlier check while the customer was still looking
        # at the code: what they are asking is whether they are paid, so answer on the order
        # rather than on what this call happened to settle.
        return order.state in ('paid', 'done')

    def _l10n_ph_kiosk_qrph_get_order(self, order_uuid):
        """ Return the open kiosk order a QRPH code is being minted or checked for.

        :param str order_uuid: uuid of the <pos.order> the kiosk is collecting
        :rtype: pos.order
        """
        self.ensure_one()
        if not self._l10n_ph_is_kiosk_qrph():
            raise ValidationError(self.env._("This payment method is not paid with a QRPH code."))
        # sudo: the kiosk is a public page, and the order it names is checked against its own config.
        order = self.env['pos.order'].sudo().search([
            ('uuid', '=', order_uuid),
            ('config_id', 'in', self.config_ids.ids),
            ('session_id.state', '!=', 'closed'),
        ], limit=1)
        if not order:
            raise ValidationError(self.env._("No open order found for this payment."))
        return order
