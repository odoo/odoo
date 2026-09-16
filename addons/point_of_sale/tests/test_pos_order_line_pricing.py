from odoo import Command
from odoo.tests import Form, tagged

from odoo.addons.point_of_sale.tests.common import TestPoSCommon


@tagged("post_install", "-at_install")
class TestPosOrderLinePricing(TestPoSCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.config = cls.basic_config
        cls.tax_src = cls.taxes["tax7"]
        cls.fpos = cls.env["account.fiscal.position"].create(
            {"name": "Map tax 7% to tax 9%"}
        )
        cls.tax_dest = cls.env["account.tax"].create(
            {
                "name": "Mapped Tax 9%",
                "amount": 9,
                "price_include_override": "tax_excluded",
                "fiscal_position_ids": [Command.link(cls.fpos.id)],
                "original_tax_ids": [Command.link(cls.tax_src.id)],
            }
        )
        cls.product = cls.create_product(
            "Pricing Probe",
            cls.categ_basic,
            lst_price=100.0,
            standard_price=50.0,
            tax_ids=cls.tax_src.ids,
        )

    def _new_order(self, **vals):
        return self.env["pos.order"].create(
            {
                "session_id": self.pos_session.id,
                "amount_tax": 0,
                "amount_total": 0,
                "amount_paid": 0,
                "amount_return": 0,
                **vals,
            }
        )

    def _add_line(self, order, qty):
        order.write(
            {
                "lines": [
                    Command.create(
                        {
                            "product_id": self.product.id,
                            "qty": qty,
                            "price_unit": 100.0,
                            "price_subtotal": 0.0,
                            "price_subtotal_incl": 0.0,
                            "tax_ids": [Command.set(self.tax_src.ids)],
                        }
                    )
                ]
            }
        )
        return order.lines

    def test_one_pricing_handler_per_trigger_field(self):
        registry = self.env["pos.order.line"]._onchange_methods
        for name in ("qty", "discount", "price_unit", "tax_ids"):
            methods = [method.__name__ for method in registry.get(name, ())]
            self.assertEqual(
                methods,
                ["_onchange_amount_line_all"],
                msg=f"{name!r} must be priced by exactly one handler, got {methods}",
            )

    def test_line_is_priced_through_the_fiscal_position(self):
        self.open_new_session()
        order = self._new_order(fiscal_position_id=self.fpos.id)
        line = self._add_line(order, qty=1)

        self.assertEqual(line.tax_ids, self.tax_src)
        self.assertEqual(line.tax_ids_after_fiscal_position, self.tax_dest)

        line._onchange_amount_line_all()
        self.assertAlmostEqual(line.price_subtotal, 100.0)
        self.assertAlmostEqual(
            line.price_subtotal_incl,
            109.0,
            msg=(
                "107.0 means the raw tax_ids were priced and the fiscal"
                " position was ignored"
            ),
        )

    def test_line_subtotals_carry_the_sign_of_their_quantity(self):
        self.open_new_session()
        for is_refund in (True, False):
            order = self._new_order(is_refund=is_refund)
            line = self._add_line(order, qty=-2)
            line._onchange_amount_line_all()

            self.assertAlmostEqual(
                line.price_subtotal,
                -200.0,
                msg=f"is_refund={is_refund}: subtotal must follow qty",
            )
            self.assertAlmostEqual(line.price_subtotal_incl, -214.0)

            order._recompute_amounts()
            self.assertAlmostEqual(order.amount_total, -214.0)

    def test_margin_is_the_plain_difference(self):
        self.open_new_session()
        order = self._new_order(is_refund=True)
        line = self._add_line(order, qty=-2)
        line._onchange_amount_line_all()
        line._update_total_cost(None)
        order.invalidate_recordset()
        line.invalidate_recordset()

        self.assertAlmostEqual(line.total_cost, -100.0)
        self.assertAlmostEqual(line.margin, -100.0)
        self.assertAlmostEqual(order.margin, -100.0)

    def test_form_created_line_keeps_the_taxes_it_was_priced_with(self):
        self.open_new_session()
        order = self._new_order()

        with Form(order) as order_form:
            with order_form.lines.new() as line_form:
                line_form.product_id = self.product
                line_form.qty = 1

        line = order.lines
        self.assertAlmostEqual(line.price_subtotal_incl, 107.0)
        self.assertEqual(
            line.tax_ids,
            self.tax_src,
            msg="the form priced the line with tax7 but did not save it",
        )

        amount_total_before = order.amount_total
        order._recompute_amounts()
        self.assertAlmostEqual(
            order.amount_total,
            amount_total_before,
            msg="the order total moved because the line's taxes were dropped",
        )


@tagged("post_install", "-at_install")
class TestPosOrderPayload(TestPoSCommon):
    AUDIT_FIELDS = {"create_date", "create_uid", "write_uid"}

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.config = cls.basic_config

    def test_payload_declares_every_field_this_module_adds(self):
        PosOrder = self.env["pos.order"]
        listed = set(PosOrder._load_pos_data_fields(self.config))
        owned = {
            name
            for name, field in PosOrder._fields.items()
            if getattr(field, "_module", None) == "point_of_sale"
        } - self.AUDIT_FIELDS
        self.assertEqual(
            sorted(owned - listed),
            [],
            msg="declared on pos.order but never sent to the POS client",
        )

    def test_payload_carries_the_receipt_access_token(self):
        self.assertIn(
            "access_token", self.env["pos.order"]._load_pos_data_fields(self.config)
        )

    def test_payload_carries_no_chatter(self):
        listed = self.env["pos.order"]._load_pos_data_fields(self.config)
        self.assertEqual(
            sorted(f for f in listed if f.startswith("message_") or f == "has_message"),
            [],
        )
