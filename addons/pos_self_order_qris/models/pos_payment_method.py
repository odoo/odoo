# Part of Odoo. See LICENSE file for full copyright and licensing details.
import logging
from datetime import timedelta

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.fields import Domain

_logger = logging.getLogger(__name__)

KIOSK_QRIS_TIMEOUT = 180

# Reusing the QR already on screen spares the acquirer a second code on a double tap.
# The margin keeps the reuse below `KIOSK_QRIS_TIMEOUT`, past which the backend calls
# the transaction expired, and leaves a retry enough time to actually be paid.
KIOSK_QRIS_REUSE_WINDOW = KIOSK_QRIS_TIMEOUT - 30


class PosPaymentMethod(models.Model):
    _inherit = "pos.payment.method"

    def _is_kiosk_qris(self):
        self.ensure_one()
        return self.payment_method_type == "bank_qr_code" and self.qr_code_method == "id_qr"

    @api.model
    def _load_pos_data_fields(self, config):
        return super()._load_pos_data_fields(config) + ["qr_code_method"]

    @api.model
    def _load_pos_self_data_domain(self, data):
        """
        Add the QRIS method to the kiosk's payment options.

        A `bank_qr_code` method has no `payment_provider`, so the base self-order domain
        (cash OR provider) leaves it out; add it back for the kiosk.
        """
        domain = super()._load_pos_self_data_domain(data)
        config = data["pos.config"]
        if config.self_ordering_mode != "kiosk":
            return domain
        qris_domain = Domain.AND([
            Domain("id", "in", config.payment_method_ids.ids),
            Domain("payment_method_type", "=", "bank_qr_code"),
            Domain("qr_code_method", "=", "id_qr"),
        ])
        return Domain.OR([qris_domain, domain])

    def _kiosk_qr_generate(self, order):
        """
        Create the QRIS QR the kiosk should display and register the transaction we
        will poll for the result.

        :param order: the ``pos.order`` being paid
        :return: ``{'qr_content': str, 'expires_in': int}`` — the EMVCo payload the kiosk
            renders itself, and the seconds left before this QR is considered expired
        :rtype: dict
        """
        bank = self.journal_id.bank_account_id.sudo()
        error = bank._get_error_messages_for_qr("id_qr", False, order.currency_id)
        if error:
            raise ValidationError(error)
        error = bank._check_for_qr_code_errors(
            "id_qr", order.amount_total, order.currency_id, False, order.name, "")
        if error:
            raise ValidationError(error)

        qr_content = bank.with_context(
            qris_model="pos.order",
            qris_model_id=order.uuid,
            qris_max_reuse_seconds=KIOSK_QRIS_REUSE_WINDOW,
        )._get_qr_vals("id_qr", order.amount_total, order.currency_id, False, order.name, "")

        return {
            "qr_content": qr_content,
            "expires_in": self._kiosk_qr_expires_in(order),
        }

    def _kiosk_qr_transactions(self, order):
        """
        The QRs issued for ``order`` that can still pay it, newest first.

        All of them are relevant, not only the one the kiosk currently displays: QRIS has
        no way to invalidate a QR, so every code handed out for this order stays payable
        for the 30 minutes the acquirer keeps it, well past the kiosk countdown. QRs for
        another amount are left out, they do not pay this order.

        :param order: the ``pos.order`` being paid
        :rtype: ``l10n_id.qris.transaction`` recordset
        """
        return self.env["l10n_id.qris.transaction"].sudo().search([
            ("model", "=", "pos.order"),
            ("model_id", "=", order.uuid),
            ("qris_amount", "=", int(order.amount_total)),
        ], order="qris_creation_datetime desc")

    def _kiosk_qr_expires_in(self, order):
        """
        Seconds left before the QR of ``order`` expires, counted from when the acquirer
        created it rather than from now: a reused QR is already partway through its life,
        and the kiosk countdown has to show the time that is actually left.

        :param order: the ``pos.order`` being paid
        :rtype: int
        """
        transactions = self._kiosk_qr_transactions(order)
        if not transactions:
            return KIOSK_QRIS_TIMEOUT
        age = (fields.Datetime.now() - transactions[0].qris_creation_datetime).total_seconds()
        return max(0, KIOSK_QRIS_TIMEOUT - int(age))

    def _kiosk_qr_fetch_status(self, order):
        """
        Return the current QRIS payment status, considering every QR issued for ``order``.

        :param order: the ``pos.order`` being paid
        :return: ``'pending'``, ``'paid'`` or ``'expired'``
        :rtype: str
        """
        transactions = self._kiosk_qr_transactions(order)
        if not transactions:
            return "expired"
        if any(transactions.mapped("paid")):
            return "paid"

        # Raises `ValidationError` if QRIS is unreachable; the caller maps that to
        # `pending` so a network blip does not fail a payment the customer may have made.
        if transactions._l10n_id_get_qris_qr_statuses()["paid"]:
            return "paid"

        age = fields.Datetime.now() - transactions[0].qris_creation_datetime
        if age > timedelta(seconds=KIOSK_QRIS_TIMEOUT):
            return "expired"
        return "pending"

    @api.model
    def _allowed_actions_in_self_order(self):
        return super()._allowed_actions_in_self_order() + [
            "kiosk_qr_create_payment",
            "kiosk_qr_poll_payment",
        ]

    def kiosk_qr_create_payment(self, order_uuid):
        """
        Give the kiosk a QR to display, unless the order turns out to be paid already.

        :return: ``{'qr_content': str, 'expires_in': int}``, or ``{'paid': True}`` if a QR
            issued earlier was paid after all
        """
        self.ensure_one()
        if not self._is_kiosk_qris():
            raise ValidationError(_("This payment method does not use QRIS QR code payments."))
        order = self._kiosk_qr_find_order(order_uuid)

        # A QR the kiosk gave up on is still payable at the acquirer, so a customer who
        # scanned one just before the countdown ran out has really paid. Settle that
        # payment rather than hand out a second QR and charge them twice.
        if self._kiosk_qr_fetch_status(order) == "paid":
            self._kiosk_qr_settle(order)
            return {"paid": True}
        return self._kiosk_qr_generate(order)

    def kiosk_qr_poll_payment(self, order_uuid):
        """
        Check the payment status and notify the kiosk once it is settled.

        :return: ``{'status': 'pending' | 'paid' | 'expired'}``
        """
        self.ensure_one()
        if not self._is_kiosk_qris():
            raise ValidationError(_("This payment method does not use QRIS QR code payments."))
        order = self._kiosk_qr_find_order(order_uuid)

        try:
            status = self._kiosk_qr_fetch_status(order)
        except (UserError, ValidationError):
            # A transient failure to reach the acquirer must not fail a live payment:
            # the customer may well have paid already. Report `pending` and let the
            # kiosk try again on its next tick.
            _logger.warning(
                "Kiosk QRIS status check failed for order %s on payment method %s",
                order_uuid, self.id, exc_info=True,
            )
            return {"status": "pending"}

        if status == "paid":
            self._kiosk_qr_settle(order)
        return {"status": status}

    def _kiosk_qr_find_order(self, order_uuid):
        self.ensure_one()
        order = self.env["pos.order"].sudo().search([
            ("uuid", "=", order_uuid),
            ("config_id", "in", self.config_ids.ids),
            ("session_id.state", "!=", "closed"),
        ], limit=1)
        if not order:
            raise ValidationError(_("No open order found for this payment."))
        return order

    def _kiosk_qr_settle(self, order):
        """
        Register the payment on ``order``, mark it paid and tell the kiosk.

        Called only from the request that just had the acquirer confirm the payment, so
        the payment is recorded by the server that verified it rather than on the kiosk's
        say-so — the kiosk only ever displays the QR. That also means a kiosk that crashes
        or loses the network right after the customer paid no longer leaves them with an
        unpaid order.

        `_send_payment_result` pushes `PAYMENT_STATUS`, which is what moves the kiosk to
        the confirmation page. It is re-sent even when the order is already paid, so a
        client that missed the message is not left waiting.
        """
        self.ensure_one()
        if order.state == "draft":
            order.add_payment({
                "amount": order.amount_total,
                "payment_date": fields.Datetime.now(),
                "payment_method_id": self.id,
                "pos_order_id": order.id,
            })
            order.action_pos_order_paid()
        order._send_payment_result("Success")
