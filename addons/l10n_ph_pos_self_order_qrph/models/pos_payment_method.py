# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models
from odoo.exceptions import ValidationError
from odoo.fields import Domain

# Maya documents no lifetime for a dynamic QRPH code, and keeps honouring one long after a kiosk
# would have moved on. This is therefore how long the kiosk waits before asking the customer what
# they want to do, not a moment where the code on screen stops being payable.
KIOSK_QRPH_TIMEOUT = 180


class PosPaymentMethod(models.Model):
    _inherit = 'pos.payment.method'

    def _l10n_ph_is_kiosk_qrph(self):
        self.ensure_one()
        return self.payment_method_type == 'bank_qr_code' and self.qr_code_method == 'ph_qrph'

    @api.model
    def _load_pos_data_fields(self, config):
        # EXTENDS point_of_sale
        # The kiosk decides on which methods it mints a QRPH code for, so it needs the method.
        return super()._load_pos_data_fields(config) + ['qr_code_method']

    @api.model
    def _load_pos_self_data_domain(self, data):
        # EXTENDS pos_self_order
        # A bank QR code method is paid without a payment provider, so the kiosk domain of cash or
        # provider leaves it out: put the QRPH one back, the kiosk knows how to show its code.
        domain = super()._load_pos_self_data_domain(data)
        config = data['pos.config']
        if config.self_ordering_mode != 'kiosk':
            return domain
        qrph_domain = Domain.AND([
            Domain('id', 'in', config.payment_method_ids.ids),
            Domain('payment_method_type', '=', 'bank_qr_code'),
            Domain('qr_code_method', '=', 'ph_qrph'),
        ])
        return Domain.OR([qrph_domain, domain])

    @api.model
    def _allowed_actions_in_self_order(self):
        # EXTENDS point_of_sale
        return super()._allowed_actions_in_self_order() + [
            'l10n_ph_kiosk_qrph_create_payment',
            'l10n_ph_kiosk_qrph_verify_payment',
        ]

    def l10n_ph_kiosk_qrph_create_payment(self, order_uuid):
        """ Give the kiosk the QRPH code to display, unless the order turns out to be paid already.

        :param str order_uuid: uuid of the <pos.order> the kiosk is collecting
        :return: ``{'qr_content': str, 'expires_in': int}``, or ``{'paid': True}`` when a code
            handed out earlier was paid after all
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
            bank._get_error_messages_for_qr('ph_qrph', order.partner_id, order.currency_id),
            bank._check_for_qr_code_errors(
                'ph_qrph', order.amount_total, order.currency_id, order.partner_id, order.name, ''),
        ):
            if error:
                raise ValidationError(error)

        # Minting is asked for the order rather than for the kiosk, so that the payment it opens on
        # Maya is the one its notification settles. Within the reuse window this hands back the code
        # already on screen, which keeps a customer tapping retry from opening a second payment.
        qr_content = bank.with_context(
            l10n_ph_qrph_model='pos.order',
            l10n_ph_qrph_model_id=order.uuid,
        )._get_qr_vals('ph_qrph', order.amount_total, order.currency_id, order.partner_id, order.name, '')

        return {'qr_content': qr_content, 'expires_in': KIOSK_QRPH_TIMEOUT}

    def l10n_ph_kiosk_qrph_verify_payment(self, order_uuid):
        """ Ask Maya about the codes issued for an order, for a customer who says they have paid.

        Maya notifies the server on its own, which is what normally moves the kiosk on. This is the
        way out when that notification is late, lost, or was never configured.

        :param str order_uuid: uuid of the <pos.order> the kiosk is collecting
        :rtype: dict
        """
        self.ensure_one()
        order = self._l10n_ph_kiosk_qrph_get_order(order_uuid)
        return {'paid': self._l10n_ph_kiosk_qrph_settle_if_paid(order)}

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
        # sudo: the codes are readable by accountants, and this runs for a customer at a kiosk.
        transactions = self.env['l10n_ph.qrph.transaction'].sudo().search([
            ('model', '=', 'pos.order'),
            ('model_id', '=', order.uuid),
        ])
        if transaction := transactions._get_paid_transaction(order.amount_total):
            transaction._l10n_ph_qrph_settle()
        # Maya's own notification may have settled the order while the customer was still looking
        # at the code: what they are asking is whether they are paid, not whose message got here
        # first, so answer on the order rather than on what this call happened to settle.
        return order.state in ('paid', 'done', 'invoiced')

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
