import json
from unittest.mock import patch

from odoo.addons.point_of_sale.tests.common import CommonPosTest
from odoo.addons.point_of_sale.tests.test_frontend import TestPointOfSaleHttpCommon
from odoo.exceptions import UserError
from odoo.fields import Command
from odoo.tests import tagged
from odoo.tools import mute_logger

OK_RESPONSE = {"InvoiceNumber": "9000052011142444901", "Code": "100", "Errors": None}


@tagged("post_install_l10n", "post_install", "-at_install")
class TestL10nPkEdiPos(CommonPosTest):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env.company.country_id = cls.env.ref("base.pk")
        cls.env.company.account_fiscal_country_id = cls.env.ref("base.pk")
        cls.env["account.tax.group"].create(
            {"name": "PK Taxes", "country_id": cls.env.ref("base.pk").id, "company_id": cls.env.company.id}
        )
        cls.pos_config_usd.write(
            {
                "l10n_pk_edi_pos_enabled": True,
                "l10n_pk_edi_pos_identifier": "110014",
                "l10n_pk_edi_pos_test_identifier": "900005",
                "l10n_pk_edi_pos_token": "prod-token",
                "l10n_pk_edi_pos_sandbox": True,
                "payment_method_ids": [Command.link(cls.cash_payment_method.id)],
            }
        )
        cls.cash_payment_method.l10n_pk_edi_pos_fbr_payment_code = "1"
        cls.tax17 = cls._create_tax("GST 17", amount=17.0)
        cls.pk_product = cls.env["product.product"].create(
            {
                "name": "PK Product",
                "type": "consu",
                "list_price": 100.0,
                "taxes_id": [Command.set(cls.tax17.ids)],
                "hs_code": "1100.1010",
                "default_code": "PK-001",
            }
        )

    @classmethod
    def _create_tax(cls, name, **vals):
        return cls.env["account.tax"].create({"name": name, "type_tax_use": "sale", "amount_type": "percent", **vals})

    @classmethod
    def _create_formula_tax(cls, name, formula, **vals):
        return cls._create_tax(name, amount_type="code", formula=formula, **vals)

    def _create_order(self, line_data, order_data=None):
        with patch.object(self.env.registry["pos.order"], "_l10n_pk_edi_pos_send"):
            order, _refund = self.create_backend_pos_order(
                {
                    "pos_config": self.pos_config_usd,
                    "line_data": line_data,
                    "order_data": order_data or {},
                    "payment_data": [{"payment_method_id": self.cash_payment_method.id}],
                }
            )
        return order

    def _make_order(self, **line_vals):
        return self._create_order([{"product_id": self.pk_product.id, "qty": 2, **line_vals}])

    def _make_refund(self):
        with patch.object(self.env.registry["pos.order"], "_l10n_pk_edi_pos_send"):
            _order, refund = self.create_backend_pos_order(
                {
                    "pos_config": self.pos_config_usd,
                    "line_data": [{"product_id": self.pk_product.id, "qty": 2}],
                    "payment_data": [{"payment_method_id": self.cash_payment_method.id}],
                    "refund_data": [{"payment_method_id": self.cash_payment_method.id}],
                }
            )
        return refund

    def _make_order_with_service_fee(self):
        fee_product = self.env.ref("l10n_pk_edi_pos.product_product_fbr_service_fee")
        return self._create_order(
            [{"product_id": self.pk_product.id, "qty": 2}, {"product_id": fee_product.id, "qty": 1}]
        )

    def _send(self, order, response=OK_RESPONSE):
        """Submit with a mocked FBR response; return the connection mock."""
        with patch.object(
            self.env.registry["pos.order"], "_l10n_pk_edi_pos_connect_to_server", return_value=response
        ) as connect:
            order._l10n_pk_edi_pos_send()
        return connect

    def _order_attachments(self, order):
        return self.env["ir.attachment"].search([("res_model", "=", "pos.order"), ("res_id", "=", order.id)])

    def _tax_scenario(self, taxes, third_schedule=False, list_price=100.0, **line_vals):
        """Reset every product field the payload prices on, so scenarios stay independent inside subTest."""
        self.pk_product.write(
            {
                "taxes_id": [Command.set(taxes.ids)],
                "l10n_pk_is_fbr_3rd_schedule": third_schedule,
                "list_price": list_price,
            }
        )
        order = self._create_order([{"product_id": self.pk_product.id, "qty": 2, **line_vals}])
        return order._l10n_pk_edi_pos_generate_json()["Items"][0]

    def test_generate_json_payload(self):
        """Every field the FBR reads is mapped: shop, order, buyer, and the lines it must be told about."""
        order = self._make_order()
        payload = order._l10n_pk_edi_pos_generate_json()
        self.assertEqual(payload["POSID"], 900005)
        self.assertEqual(payload["InvoiceType"], 1)
        self.assertEqual(payload["PaymentMode"], 1)
        self.assertEqual(payload["USIN"], order.pos_reference.replace(" ", "")[:50])
        self.assertEqual(len(payload["Items"]), 1)
        item = payload["Items"][0]
        self.assertEqual(item["PCTCode"], "11001010")
        self.assertEqual(item["ItemCode"], "PK-001")
        self.assertEqual(item["Quantity"], 2.0)
        self.assertEqual(item["TaxRate"], 17.0)
        self.assertEqual(item["InvoiceType"], 1)
        self.assertEqual(payload["TotalQuantity"], 2.0)
        self.assertEqual(payload["TotalSaleValue"], item["SaleValue"])
        self.assertEqual(payload["TotalTaxCharged"], item["TaxCharged"])
        self.assertEqual(payload["TotalBillAmount"], abs(order.amount_total))
        self.assertEqual(payload["TotalTaxCharged"], abs(order.amount_tax))
        self.assertEqual(payload["TotalSaleValue"] + payload["TotalTaxCharged"], payload["TotalBillAmount"])
        self.assertEqual(payload["BuyerName"], "")
        self.assertEqual(payload["BuyerNTN"], "")
        self.assertEqual(payload["BuyerCNIC"], "")

        partner = self.env["res.partner"].create(
            {"name": "PK Buyer", "phone": "+92 300 1234567", "country_id": self.env.ref("base.pk").id, "vat": "4174942"}
        )
        partner._set_additional_identifier("PK_CN", "4210112345678")
        identified = self._create_order(
            [{"product_id": self.pk_product.id, "qty": 1}], order_data={"partner_id": partner.id}
        )
        payload = identified._l10n_pk_edi_pos_generate_json()
        self.assertEqual(payload["BuyerName"], "PK Buyer")
        self.assertEqual(payload["BuyerPhoneNumber"], "+92 300 1234567")
        self.assertEqual(payload["BuyerNTN"], "4174942")
        self.assertEqual(payload["BuyerCNIC"], "42101-1234567-8")

        # A refund is reported positively under its own invoice type.
        payload = self._make_refund()._l10n_pk_edi_pos_generate_json()
        self.assertEqual(payload["InvoiceType"], 3)
        item = payload["Items"][0]
        self.assertEqual(item["InvoiceType"], 3)
        self.assertEqual(item["Quantity"], 2.0)
        self.assertEqual(item["SaleValue"], 200.0)
        self.assertEqual(item["TaxCharged"], 34.0)
        self.assertEqual(payload["TotalBillAmount"], 234.0)

        # The service fee is ours, not a sold item, so the FBR never hears about it.
        payload = self._make_order_with_service_fee()._l10n_pk_edi_pos_generate_json()
        self.assertEqual(len(payload["Items"]), 1)
        self.assertEqual(payload["TotalQuantity"], 2.0)
        self.assertEqual(payload["TotalSaleValue"], 201.0)
        self.assertEqual(payload["TotalBillAmount"], 235.0)
        self.assertEqual(payload["TotalTaxCharged"], 34.0)

    def test_generate_json_tax_shapes(self):
        """The FBR rejects an invoice whose TaxRate and TaxCharged disagree with the line, so price each tax shape exactly."""
        further = self._create_tax("Further Tax 3", amount=3.0, l10n_pk_is_further_tax=True)
        included = self._create_tax("GST 17 Included", amount=17.0, price_include_override="tax_included")
        formula = self._create_formula_tax("GST 18 3rd", "quantity * (product.lst_price * 0.18)")
        formula_included = self._create_formula_tax(
            "GST 18 3rd Included", "quantity * (product.lst_price * 18 / 118)", price_include_override="tax_included"
        )
        scenarios = [
            (
                "further tax is reported apart from the rate",
                {"taxes": self.tax17 + further},
                {"SaleValue": 200.0, "FurtherTax": 6.0, "TaxCharged": 34.0, "TaxRate": 17.0, "TotalAmount": 240.0},
            ),
            (
                "discount",
                {"taxes": self.tax17, "discount": 10},
                {"SaleValue": 200.0, "Discount": 20.0, "TaxCharged": 30.6, "TotalAmount": 210.6},
            ),
            (
                "discount on a tax-included price",
                {"taxes": included, "discount": 10},
                {"SaleValue": 170.94, "Discount": 17.09, "TaxCharged": 26.15, "TotalAmount": 180.0},
            ),
            (
                "3rd schedule prices on the retail price and reports its own invoice type",
                {"taxes": formula, "third_schedule": True},
                {"TaxCharged": 36.0, "TaxRate": 18.0, "InvoiceType": 11},
            ),
            (
                "3rd schedule keeps the retail rate through a discount",
                {"taxes": formula, "third_schedule": True, "discount": 10},
                {"TaxCharged": 36.0, "TaxRate": 18.0, "SaleValue": 200.0, "Discount": 20.0, "TotalAmount": 216.0},
            ),
            (
                "3rd schedule on a tax-included price",
                {"taxes": formula_included, "third_schedule": True},
                {"TaxCharged": 30.51, "SaleValue": 169.49, "TaxRate": 18.0, "TotalAmount": 200.0},
            ),
            (
                "3rd schedule on a tax-included price, discounted",
                {"taxes": formula_included, "third_schedule": True, "discount": 10},
                {"TaxCharged": 30.51, "TaxRate": 18.0, "SaleValue": 169.49, "Discount": 20.0, "TotalAmount": 180.0},
            ),
            (
                "a formula tax outside the 3rd schedule derives its rate from the discounted base",
                {"taxes": formula, "discount": 10},
                {"TaxCharged": 36.0, "TaxRate": 20.0},
            ),
            (
                "a derived rate is rounded to two decimals",
                {"taxes": formula, "qty": 3, "discount": 33.33},
                {"TaxRate": 27.0},
            ),
            (
                "a derived rate is not thrown off by a rounding",
                {"taxes": formula, "list_price": 12.49, "qty": 4},
                {"TaxCharged": 8.99, "TaxRate": 18.0},
            ),
        ]
        for label, setup, expected in scenarios:
            with self.subTest(label):
                item = self._tax_scenario(**setup)
                self.assertEqual({key: item[key] for key in expected}, expected)

    def test_untaxed_line_blocks_the_sale(self):
        """Further tax is no substitute for a sales tax, and an untaxed line is stopped rather than reported."""
        further = self._create_tax("Further Tax 3", amount=3.0, l10n_pk_is_further_tax=True)
        for label, taxes in (("no tax at all", self.env["account.tax"]), ("further tax only", further)):
            with self.subTest(label):
                self.pk_product.taxes_id = [Command.set(taxes.ids)]
                order = self._make_order()
                # The guard is not a check_data error: it blocks the sale instead of failing the submission.
                self.assertFalse(order._l10n_pk_edi_pos_check_data())
                with self.assertRaisesRegex(UserError, "no sales tax"):
                    order._l10n_pk_edi_pos_send()
                with self.assertRaisesRegex(UserError, "no sales tax"):
                    self._make_order()._process_saved_order(draft=False)

    def test_wrong_way_line_blocks_the_sale(self):
        """A line going the other way than its order is a cart mistake, so it stops the sale too."""
        order = self._create_order(
            [{"product_id": self.pk_product.id, "qty": 2}, {"product_id": self.pk_product.id, "qty": -1}]
        )
        self.assertFalse(order._l10n_pk_edi_pos_check_data())
        with self.assertRaisesRegex(UserError, "go against the order"):
            order._l10n_pk_edi_pos_send()

        refund = self._make_refund()
        self.assertFalse(refund._l10n_pk_edi_pos_wrong_way_lines())
        refund.lines[0].qty = 2
        with self.assertRaisesRegex(UserError, "go against the order"):
            refund._l10n_pk_edi_pos_send()

    def test_bad_data_never_reaches_the_fbr(self):
        """Every reason is gathered in one pass, and a failing order is never submitted."""
        self.assertFalse(self._make_order()._l10n_pk_edi_pos_check_data())
        self.assertFalse(self._make_refund()._l10n_pk_edi_pos_check_data())
        self.assertFalse(self._make_order_with_service_fee()._l10n_pk_edi_pos_check_data())

        self.pos_config_usd.l10n_pk_edi_pos_test_identifier = False
        self.cash_payment_method.l10n_pk_edi_pos_fbr_payment_code = False
        self.pk_product.write({"hs_code": False, "default_code": False})
        order = self._create_order(
            [
                {"product_id": self.pk_product.id, "qty": 1},
                {"product_id": self.pk_product.id, "qty": 1, "price_unit": -20.0},
            ]
        )
        errors = order._l10n_pk_edi_pos_check_data()
        self.assertEqual(len(errors), 5)
        for expected in ("FBR Shop ID", "FBR Payment Code", "global discounts", "HS Code", "Internal Reference"):
            self.assertTrue(any(expected in error for error in errors), expected)

        connect = self._send(order)
        connect.assert_not_called()
        self.assertEqual(order.l10n_pk_edi_pos_state, "unsuccessful")
        self.assertIn("FBR Payment Code", order.l10n_pk_edi_pos_error)
        self.assertIn("Internal Reference", order.l10n_pk_edi_pos_error)

    def test_send_records_the_fbr_answer(self):
        """The answer decides the state, what is kept on the order, and what the invoice shows."""
        parse = self.env["pos.order"]._l10n_pk_edi_pos_parse_response
        self.assertIsNone(parse(OK_RESPONSE))
        self.assertEqual(parse({"InvoiceNumber": "", "Code": "400", "Errors": "Invalid POSID"}), "Invalid POSID")
        self.assertEqual(
            parse({"error": {"code": "CONNECTION_ERROR", "message": "connection unsuccessful"}}), "connection unsuccessful"
        )
        self.assertEqual(parse({"error": "not_enterprise"}), "not_enterprise")
        self.assertTrue(parse({"InvoiceNumber": "", "Code": "100", "Errors": None}))

        partner = self.env["res.partner"].create({"name": "PK Buyer"})
        accepted = self._create_order(
            [{"product_id": self.pk_product.id, "qty": 2}], order_data={"partner_id": partner.id}
        )
        connect = self._send(accepted)
        self.assertEqual(accepted.l10n_pk_edi_pos_state, "successful_demo")
        self.assertEqual(accepted.l10n_pk_edi_pos_invoice_number, "9000052011142444901")
        self.assertEqual(accepted.l10n_pk_edi_pos_qr, "9000052011142444901")
        self.assertFalse(accepted.l10n_pk_edi_pos_error)
        auth_token, payload = connect.call_args.args[1:3]
        self.assertEqual(auth_token, "1298b5eb-b252-3d97-8622-a4a69d5bf818")
        self.assertEqual(payload["POSID"], 900005)
        attachments = self._order_attachments(accepted)
        self.assertEqual(len(attachments), 1)
        self.assertEqual(attachments.name, f"FBR Request {accepted._l10n_pk_edi_pos_usin()}.json")
        self.assertEqual(json.loads(attachments.raw.content)["USIN"], accepted._l10n_pk_edi_pos_usin())
        accepted.action_pos_order_invoice()
        self.assertEqual(accepted.account_move._l10n_pk_edi_pos_qr(), "9000052011142444901")

        rejected = self._make_order()
        self._send(rejected, response={"InvoiceNumber": "", "Code": "400", "Errors": "Invalid POSID"})
        self.assertEqual(rejected.l10n_pk_edi_pos_state, "unsuccessful")
        self.assertEqual(rejected.l10n_pk_edi_pos_error, "Invalid POSID")
        self.assertFalse(rejected.l10n_pk_edi_pos_invoice_number)
        # A refused payload stays downloadable from the order form instead of piling up as attachments.
        self.assertFalse(self._order_attachments(rejected))
        self.assertTrue(rejected.l10n_pk_edi_pos_payload)
        self.assertIn("l10n_pk_edi_pos_payload", rejected.download_l10n_pk_edi_pos_payload()["url"])

        self.pos_config_usd.l10n_pk_edi_pos_sandbox = False
        production = self._make_order()
        connect = self._send(production)
        self.assertEqual(production.l10n_pk_edi_pos_state, "successful")
        auth_token, payload = connect.call_args.args[1:3]
        self.assertEqual(auth_token, "prod-token")
        self.assertEqual(payload["POSID"], 110014)

    @mute_logger("odoo.addons.l10n_pk_edi_pos.models.pos_order")
    def test_send_entry_points(self):
        """Closing an order submits it and resending retries it, without ever taking the session down."""
        with patch.object(self.env.registry["pos.order"], "_l10n_pk_edi_pos_connect_to_server", return_value=OK_RESPONSE):
            closed = self._make_order()
            closed._process_saved_order(draft=False)
            self.assertEqual(closed.l10n_pk_edi_pos_state, "successful_demo")

            retried = self._make_order()
            retried.l10n_pk_edi_pos_state = "unsuccessful"
            retried.action_l10n_pk_edi_pos_resend()
            self.assertEqual(retried.l10n_pk_edi_pos_state, "successful_demo")

        unreachable = self._make_order()
        with patch.object(
            self.env.registry["pos.order"],
            "_l10n_pk_edi_pos_connect_to_server",
            side_effect=ValueError("connection unsuccessful"),
        ):
            unreachable._process_saved_order(draft=False)
        self.assertEqual(unreachable.l10n_pk_edi_pos_state, "unsuccessful")
        self.assertIn("connection unsuccessful", unreachable.l10n_pk_edi_pos_error)
        self.assertFalse(unreachable.to_invoice)

        self.pos_config_usd.l10n_pk_edi_pos_enabled = False
        disabled = self._make_order()
        with patch.object(self.env.registry["pos.order"], "_l10n_pk_edi_pos_send") as send:
            disabled._process_saved_order(draft=False)
            send.assert_not_called()
        self.assertEqual(disabled.l10n_pk_edi_pos_state, "to_send")


@tagged("post_install_l10n", "post_install", "-at_install")
class TestL10nPkEdiPosTours(TestPointOfSaleHttpCommon):
    def test_global_discount_button_disabled(self):
        discount_product = self.env["product.product"].create({"name": "Discount", "available_in_pos": True})
        self.main_pos_config.write(
            {"l10n_pk_edi_pos_enabled": True, "module_pos_discount": True, "discount_product_id": discount_product.id}
        )
        self.main_pos_config.with_user(self.pos_user).open_ui()
        self.start_pos_tour("l10n_pk_edi_pos_discount_disabled_tour")

    def test_fbr_service_fee_line_added(self):
        self.main_pos_config.write({"l10n_pk_edi_pos_charge_service_fee": True})
        self.main_pos_config.with_user(self.pos_user).open_ui()
        self.start_pos_tour("l10n_pk_edi_pos_service_fee_tour")

    def test_fbr_service_fee_product_is_configurable(self):
        fee_product = self.env["product.product"].create(
            {"name": "Shop Service Charge", "type": "service", "list_price": 5.0, "available_in_pos": False, "taxes_id": [Command.clear()]}
        )
        self.main_pos_config.write(
            {"l10n_pk_edi_pos_charge_service_fee": True, "l10n_pk_edi_pos_service_fee_product_id": fee_product.id}
        )
        self.main_pos_config.with_user(self.pos_user).open_ui()
        self.start_pos_tour("l10n_pk_edi_pos_custom_service_fee_tour")
