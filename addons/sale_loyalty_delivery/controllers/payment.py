from odoo import _
from odoo.exceptions import ValidationError

from odoo.addons.payment.controllers import portal as payment_portal


class PaymentPortal(payment_portal.PaymentPortal):

    def _create_transaction(self, *args, **kwargs):
        tx = super()._create_transaction(*args, **kwargs)
        for order in tx.sale_order_ids:
            if (
                tx.provider_id.custom_mode in tx.provider_id._get_pay_on_delivery_provider_codes() and
                order.coupon_point_ids.filtered(lambda pe: pe.coupon_id.program_id.program_type in ['gift_card', 'ewallet']).coupon_id
            ):
                raise ValidationError(
                    _("Cannot process payment: Gift cards and eWallets are not compatible with on site payment")
                )
        return tx
