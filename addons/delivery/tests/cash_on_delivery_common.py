# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.fields import Command

from odoo.addons.delivery.tests.common import DeliveryCommon
from odoo.addons.payment_custom.tests.common import PaymentCustomCommon


class CashOnDeliveryCommon(PaymentCustomCommon, DeliveryCommon):
    _test_user_groups = ("sales_team.group_sale_salesman",)

    _test_user_name = "Test Sales User"

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.sale_order = cls._create_so(
            order_line=[Command.create({"product_id": cls.product.id, "product_uom_qty": 5})]
        )
        cls.free_delivery.allow_cash_on_delivery = True
        cls.sale_order.set_delivery_line(cls.free_delivery, 0)
        cls.cod_provider = cls._prepare_provider(code="custom", custom_mode="cash_on_delivery")
        cls.cod_provider.with_context(active_test=False).payment_method_ids.active = True

    @classmethod
    def _create_cod_transaction(cls, sale_order=None, **values):
        sale_order = (sale_order or cls.sale_order).ensure_one()
        default_values = {
            "sale_order_ids": [Command.set(sale_order.ids)],
            "partner_id": sale_order.partner_id.id,
            "amount": sale_order.amount_total,
            "currency_id": sale_order.currency_id.id,
            "state": "pending",
            "provider_id": cls.cod_provider.id,
            "payment_method_id": cls.cod_provider.payment_method_ids.id,
            "reference": False,  # Force the computation of an unique reference
        }
        return cls._create_transaction(cls, flow="direct", **{**default_values, **values})
