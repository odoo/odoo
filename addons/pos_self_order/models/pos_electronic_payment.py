from odoo import fields, models
from odoo.exceptions import ValidationError


class PosElectronicPayment(models.Model):
    _inherit = "pos.electronic.payment"

    pos_payment_method_ids = fields.One2many("pos.payment.method", "electronic_payment_id")

    ####################
    #  Helper methods  #
    ####################

    def _kiosk_get_payment_data_from_result(self, transaction_id: str, result: dict):
        return {
            "transaction_id": result.get("final_transaction_id") or transaction_id,
            "card_type": result.get("card_type"),
            "card_no": result.get("card_no"),
            "card_brand": result.get("card_brand"),
            "cardholder_name": result.get("cardholder_name"),
            "payment_method_metadata": result.get("metadata"),
        }

    def _kiosk_get_order_and_payment_method(self, amount: float, currency, extra_args: dict):
        payment_method_id = extra_args.get("kiosk_payment_method_id")
        order_id = extra_args.get("kiosk_order_id")

        if not payment_method_id or not order_id:
            return None, None

        payment_method = self.env["pos.payment.method"].browse(payment_method_id).exists()
        order = self.env["pos.order"].browse(order_id).exists()

        if (
            not payment_method or
            not order or
            order.state != "draft" or
            order.config_id.self_ordering_mode != "kiosk" or
            currency != order.currency_id or
            payment_method.electronic_payment_id != self or
            payment_method not in order.config_id.payment_method_ids or
            currency.compare_amounts(order.amount_total, amount) != 0
        ):
            raise ValidationError(self.env._("The kiosk payment could not be processed."))

        return order, payment_method

    def _kiosk_get_pending_payment(self, transaction_id: str):
        kiosk_payment = self.env["pos.payment"].search([
            ("payment_method_id", "in", self.pos_payment_method_ids.ids),
            ("transaction_id", "=", transaction_id),
            ("payment_status", "=", "pending"),
        ], limit=1)
        if not kiosk_payment:
            return None

        order = kiosk_payment.pos_order_id
        payment_method = kiosk_payment.payment_method_id
        config = order.config_id

        if (
            order.state != "draft" or
            config.self_ordering_mode != "kiosk" or
            payment_method not in config.payment_method_ids or
            payment_method.electronic_payment_id != self
        ):
            return None

        return kiosk_payment

    def _kiosk_validate_pending_payment(self, transaction_id: str, result: dict):
        kiosk_payment = self._kiosk_get_pending_payment(transaction_id)
        if kiosk_payment:
            kiosk_payment.write({
                **self._kiosk_get_payment_data_from_result(transaction_id, result),
                "payment_status": "done",
            })
            kiosk_payment.pos_order_id.write({'amount_paid': kiosk_payment.pos_order_id._compute_amount_paid()})
            kiosk_payment.pos_order_id.action_pos_order_paid()
            kiosk_payment.pos_order_id._send_payment_result("Success")

    def _kiosk_delete_pending_payment(self, transaction_id: str):
        kiosk_payment = self._kiosk_get_pending_payment(transaction_id)
        if kiosk_payment:
            kiosk_payment.unlink()

    def _kiosk_add_pending_payment(self, amount: float, currency, extra_args: dict, result: dict):
        order, payment_method = self._kiosk_get_order_and_payment_method(amount, currency, extra_args)
        if not order or not payment_method:
            return

        order.add_payment({
            "amount": amount,
            "payment_method_id": payment_method.id,
            "pos_order_id": order.id,
            "payment_status": "pending",
            "transaction_id": result["transaction_id"],
            "payment_method_metadata": result.get("metadata"),
        })

    def _kiosk_add_payment_and_validate(self, amount: float, currency, extra_args: dict, result: dict):
        order, payment_method = self._kiosk_get_order_and_payment_method(amount, currency, extra_args)
        if not order or not payment_method:
            return

        order.add_payment({
            "amount": amount,
            "payment_method_id": payment_method.id,
            "pos_order_id": order.id,
            "payment_status": "done",
            **self._kiosk_get_payment_data_from_result(result["transaction_id"], result),
        })
        order.action_pos_order_paid()
        order._send_payment_result("Success")

    ###################
    #    Overrides    #
    ###################

    def _start_payment(self, amount: float, currency, extra_args: dict):
        result = super()._start_payment(amount, currency, extra_args)
        status = result.get("status", "pending")
        if status == "paid":
            self._kiosk_add_payment_and_validate(amount, currency, extra_args, result)
        elif status == "pending":
            self._kiosk_add_pending_payment(amount, currency, extra_args, result)
        return result

    def _notify(self, transaction_id: str, data: dict):
        if data["status"] == "paid":
            self._kiosk_validate_pending_payment(transaction_id, data)
        elif data["status"] == "failed":
            self._kiosk_delete_pending_payment(transaction_id)
        return super()._notify(transaction_id, data)

    def _get_transaction_status(self, transaction_id: str):
        result = super()._get_transaction_status(transaction_id)

        if result["status"] == "paid":
            self._kiosk_validate_pending_payment(transaction_id, result)
        elif result["status"] == "failed":
            self._kiosk_delete_pending_payment(transaction_id)
        return result
