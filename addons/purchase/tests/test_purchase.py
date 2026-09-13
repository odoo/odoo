from datetime import timedelta

from freezegun import freeze_time
from psycopg.errors import IntegrityError

from odoo import Command, fields
from odoo.exceptions import UserError
from odoo.libs.datetime import timezone
from odoo.tests import Form, tagged
from odoo.tools import mute_logger

from odoo.addons.account.tests.common import AccountTestInvoicingCommon


@tagged("-at_install", "post_install")
class TestPurchase(AccountTestInvoicingCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company_data_2 = cls.setup_other_company()

    def test_date_commitment(self):
        po = Form(self.env["purchase.order"])
        po.partner_id = self.partner_a
        with po.line_ids.new() as po_line:
            po_line.product_id = self.product_a
            po_line.product_qty = 1
            po_line.price_unit = 100
        with po.line_ids.new() as po_line:
            po_line.product_id = self.product_b
            po_line.product_qty = 10
            po_line.price_unit = 200
        po = po.save()

        self.assertNotEqual(po.line_ids[0].date_commitment, False)
        self.assertAlmostEqual(
            po.line_ids[0].date_commitment,
            po.line_ids[1].date_commitment,
            delta=timedelta(seconds=10),
        )
        self.assertAlmostEqual(
            po.line_ids[0].date_commitment,
            po.date_commitment,
            delta=timedelta(seconds=10),
        )

        orig_date_commitment = po.line_ids[0].date_commitment

        new_date_commitment = orig_date_commitment - timedelta(hours=1)
        po.line_ids[0].date_commitment = new_date_commitment
        self.assertAlmostEqual(
            po.line_ids[0].date_commitment,
            po.date_commitment,
            delta=timedelta(seconds=10),
        )

        new_date_commitment_2 = orig_date_commitment - timedelta(hours=72)
        po_form = Form(po)
        with po_form.line_ids.edit(1) as po_line:
            po_line.date_commitment = new_date_commitment_2
        po = po_form.save()
        self.assertAlmostEqual(
            po.line_ids[1].date_commitment,
            po.date_commitment,
            delta=timedelta(seconds=10),
        )
        self.assertAlmostEqual(
            po.line_ids[0].date_commitment,
            new_date_commitment,
            delta=timedelta(seconds=10),
        )

    def test_date_commitment_2(self):
        po = self.env["purchase.order"].create(
            {
                "partner_id": self.partner_a.id,
                "line_ids": [
                    Command.create(
                        {
                            "name": self.product_a.name,
                            "product_id": self.product_a.id,
                            "product_qty": 10,
                            "product_uom_id": self.product_a.uom_id.id,
                            "price_unit": 1,
                        }
                    )
                ],
            }
        )
        with Form(po) as po_form:
            po_form.date_commitment = fields.Datetime.now() + timedelta(days=1)
        self.assertEqual(po.line_ids.date_commitment, po.date_commitment)

        with Form(po) as po_form:
            with po_form.line_ids.new() as new_line:
                new_line.product_id = self.product_b
                new_line.product_qty = 10
                new_line.price_unit = 200
        self.assertEqual(po.line_ids[1].date_commitment, po.date_commitment)
        self.assertNotEqual(po.line_ids[0].date_commitment, po.date_commitment)

    def test_purchase_order_sequence(self):
        PurchaseOrder = self.env["purchase.order"].with_context(tracking_disable=True)
        company = self.env.user.company_id
        self.env["ir.sequence"].search(
            [
                ("code", "=", "purchase.order"),
            ]
        ).write(
            {
                "use_date_range": True,
                "prefix": "PO/%(range_year)s/",
            }
        )
        vals = {
            "partner_id": self.partner_a.id,
            "company_id": company.id,
            "currency_id": company.currency_id.id,
            "date_order": "2019-01-01",
        }
        purchase_order = PurchaseOrder.create(vals.copy())
        self.assertTrue(purchase_order.name.startswith("PO/2019/"))
        vals["date_order"] = "2020-01-01"
        purchase_order = PurchaseOrder.create(vals.copy())
        self.assertTrue(purchase_order.name.startswith("PO/2020/"))
        vals["date_order"] = "2019-12-31 23:30:00"
        purchase_order = PurchaseOrder.with_context(tz="Europe/Brussels").create(
            vals.copy()
        )
        self.assertTrue(purchase_order.name.startswith("PO/2020/"))

    def test_reminder_1(self):
        self.partner_a.with_company(
            self.company_data_2["company"]
        ).receipt_reminder_email = True
        self.partner_a.with_company(
            self.company_data_2["company"]
        ).reminder_date_before_receipt = 1
        self.env.user.tz = "Europe/Brussels"
        po = Form(self.env["purchase.order"])
        po.partner_id = self.partner_a
        with po.line_ids.new() as po_line:
            po_line.product_id = self.product_a
            po_line.product_qty = 1
            po_line.price_unit = 100
        with po.line_ids.new() as po_line:
            po_line.product_id = self.product_b
            po_line.product_qty = 10
            po_line.price_unit = 200
        date_commitment = fields.Datetime.now().replace(hour=23, minute=0) + timedelta(
            days=2
        )
        po.date_commitment = date_commitment
        po = po.save()
        po.action_confirm()
        self.assertEqual(po.company_id, self.company)
        self.assertFalse(po.receipt_reminder_email)
        self.assertEqual(
            po.reminder_date_before_receipt,
            1,
            "The default value should be taken from the company",
        )
        old_messages = po.message_ids
        po._send_reminder_mail()
        messages_send = po.message_ids - old_messages
        self.assertFalse(messages_send)
        self.partner_a.receipt_reminder_email = True
        self.partner_a.reminder_date_before_receipt = 2
        self.env.invalidate_all()
        self.assertTrue(po.receipt_reminder_email)
        self.assertEqual(po.reminder_date_before_receipt, 2)

        self.assertEqual(po.date_commitment, date_commitment)
        po_tz = timezone(po.user_id.tz)
        localized_date_commitment = po.date_commitment.astimezone(po_tz)
        self.assertEqual(localized_date_commitment, po.get_localized_date_commitment())
        self.assertEqual(
            localized_date_commitment,
            po.get_localized_date_commitment(
                po.date_commitment.strftime("%Y-%m-%d %H:%M:%S")
            ),
        )

        self.assertFalse(
            po.partner_id in po.message_partner_ids,
            "Customer should not automatically be added in followers",
        )

        old_messages = po.message_ids
        po._send_reminder_mail()
        messages_send = po.message_ids - old_messages
        self.assertTrue(messages_send)
        self.assertFalse(
            po.partner_id in po.message_partner_ids,
            "Customer should not automatically be added in followers",
        )

        po.action_acknowledge()
        self.assertTrue(po.acknowledged)

    def test_reminder_2(self):
        po = Form(self.env["purchase.order"])
        po.partner_id = self.partner_a
        with po.line_ids.new() as po_line:
            po_line.product_id = self.product_a
            po_line.product_qty = 1
            po_line.price_unit = 100
        with po.line_ids.new() as po_line:
            po_line.product_id = self.product_b
            po_line.product_qty = 10
            po_line.price_unit = 200
        po.date_commitment = fields.Datetime.now() + timedelta(days=2)
        po = po.save()
        self.partner_a.receipt_reminder_email = True
        self.partner_a.reminder_date_before_receipt = 1
        po.action_confirm()

        self.assertFalse(
            po.partner_id in po.message_partner_ids,
            "Customer should not automatically be added in followers",
        )

        old_messages = po.message_ids
        po._send_reminder_mail()
        messages_send = po.message_ids - old_messages
        self.assertFalse(messages_send)

    def test_update_date_commitment(self):
        po = Form(self.env["purchase.order"])
        po.partner_id = self.partner_a
        with po.line_ids.new() as po_line:
            po_line.product_id = self.product_a
            po_line.product_qty = 1
            po_line.price_unit = 100
            po_line.date_commitment = "2020-06-06 00:00:00"
        with po.line_ids.new() as po_line:
            po_line.product_id = self.product_b
            po_line.product_qty = 10
            po_line.price_unit = 200
            po_line.date_commitment = "2020-06-06 00:00:00"
        po = po.save()
        po.action_confirm()

        po._update_order_lines_date_commitment(
            [(po.line_ids[0], fields.Datetime.today())]
        )
        self.assertEqual(po.line_ids[0].date_commitment, fields.Datetime.today())
        activity = self.env["mail.activity"].search(
            [
                ("summary", "=", "Date Updated"),
                ("res_model_id", "=", "purchase.order"),
                ("res_id", "=", po.id),
            ]
        )
        self.assertTrue(activity)
        self.assertIn(
            "<p>partner_a modified receipt dates for the following products:</p>\n"
            "<p> - product_a from 2020-06-06 to %s</p>" % fields.Date.today(),
            activity.note,
        )

        po._update_order_lines_date_commitment(
            [(po.line_ids[1], fields.Datetime.today())]
        )
        self.assertEqual(po.line_ids[1].date_commitment, fields.Datetime.today())
        self.assertIn(
            "<p>partner_a modified receipt dates for the following products:</p>\n"
            "<p> - product_a from 2020-06-06 to %(today)s</p>\n"
            "<p> - product_b from 2020-06-06 to %(today)s</p>"
            % {"today": fields.Date.today()},
            activity.note,
        )

    def test_with_different_uom(self):
        self.env.user.group_ids += self.env.ref("uom.group_uom")
        uom_units = self.env.ref("uom.product_uom_unit")
        uom_dozens = self.env.ref("uom.product_uom_dozen")
        uom_pairs = self.env["uom.uom"].create(
            {
                "name": "Pairs",
                "relative_factor": 2,
                "relative_uom_id": uom_units.id,
            }
        )
        product_data = {
            "name": "SuperProduct",
            "type": "consu",
            "uom_id": uom_units.id,
            "seller_ids": [
                Command.create(
                    {
                        "partner_id": self.partner_a.id,
                        "product_uom_id": uom_pairs.id,
                        "price": 200,
                    }
                )
            ],
        }
        product_01 = self.env["product.product"].create(product_data)
        product_02 = self.env["product.product"].create(product_data)

        po_form = Form(self.env["purchase.order"])
        po_form.partner_id = self.partner_a
        with po_form.line_ids.new() as po_line:
            po_line.product_id = product_01
        with po_form.line_ids.new() as po_line:
            po_line.product_id = product_02
            po_line.product_uom_id = uom_dozens
        po = po_form.save()

        self.assertEqual(po.line_ids[0].price_unit, 200)
        self.assertEqual(
            po.line_ids[1].price_unit,
            0,
            "No vendor with matching UoM is found, so price should be 0",
        )

    def test_on_change_quantity_description(self):
        self.env.user.write({"company_id": self.company_data["company"].id})

        po = Form(self.env["purchase.order"])
        po.partner_id = self.partner_a
        with po.line_ids.new() as pol:
            pol.product_id = self.product_a
            pol.product_qty = 1

        pol.name = "New custom description"
        pol.product_qty += 1
        self.assertEqual(pol.name, "New custom description")

    def test_purchase_multicurrency(self):
        self.env["decimal.precision"].search(
            [
                ("name", "=", "Product Price"),
            ]
        ).digits = 5
        product = self.env["product.product"].create(
            {
                "name": "product_test",
                "uom_id": self.env.ref("uom.product_uom_unit").id,
                "lst_price": 10.0,
                "standard_price": 0.12345,
            }
        )
        currency = self.env["res.currency"].create(
            {
                "name": "Dark Chocolate Coin",
                "symbol": "🍫",
                "rounding": 0.001,
                "position": "after",
                "currency_unit_label": "Dark Choco",
                "currency_subunit_label": "Dark Cacao Powder",
            }
        )
        currency_rate = self.env["res.currency.rate"].create(
            {
                "name": "2016-01-01",
                "rate": 2,
                "currency_id": currency.id,
                "company_id": self.env.company.id,
            }
        )

        po_form = Form(self.env["purchase.order"])
        po_form.partner_id = self.partner_a
        with po_form.line_ids.new() as po_line:
            po_line.product_id = product
        purchase_order_usd = po_form.save()
        self.assertEqual(
            purchase_order_usd.line_ids.price_unit,
            product.standard_price,
            "Value shouldn't be rounded $",
        )

        po_form = Form(self.env["purchase.order"])
        po_form.partner_id = self.partner_a
        po_form.currency_id = currency
        with po_form.line_ids.new() as po_line:
            po_line.product_id = product
        purchase_order_coco = po_form.save()
        self.assertEqual(
            purchase_order_coco.line_ids.price_unit,
            currency_rate.rate * product.standard_price,
            "Value shouldn't be rounded 🍫",
        )

        company_a = self.company_data["company"]
        company_b = self.company_data_2["company"]

        company_b.currency_id = currency

        self.env["res.currency.rate"].create(
            {
                "name": "2023-01-01",
                "rate": 2,
                "currency_id": currency.id,
                "company_id": company_b.id,
            }
        )

        product_b = (
            self.env["product.product"]
            .with_company(company_a)
            .create(
                {
                    "name": "product_2",
                    "uom_id": self.env.ref("uom.product_uom_unit").id,
                    "standard_price": 0.0,
                }
            )
        )

        self.assertEqual(
            product_b.cost_currency_id,
            company_a.currency_id,
            "The cost currency should be the one set on the company",
        )

        product_b = product_b.with_company(company_b)

        self.assertEqual(
            product_b.cost_currency_id,
            currency,
            "The cost currency should be the one set on the company,"
            " as the product is now opened in another company",
        )

        product_b.supplier_taxes_id = False
        product_b.update({"standard_price": 10.0})

        order_b = (
            self.env["purchase.order"]
            .with_company(company_b)
            .create(
                {
                    "partner_id": self.partner_a.id,
                    "line_ids": [
                        (
                            0,
                            0,
                            {
                                "product_id": product_b.id,
                                "product_qty": 1,
                                "product_uom_id": self.env.ref(
                                    "uom.product_uom_unit"
                                ).id,
                            },
                        )
                    ],
                }
            )
        )

        self.assertEqual(
            order_b.line_ids.price_unit, 10.0, "The price unit should be 10.0"
        )

    def test_discount_and_price_update_on_quantity_change(self):
        product = self.env["product.product"].create(
            {
                "name": "Product",
                "standard_price": 12,
                "seller_ids": [
                    Command.create(
                        {
                            "partner_id": self.partner_a.id,
                            "min_qty": 10,
                            "price": 10,
                            "discount": 10,
                        }
                    ),
                    Command.create(
                        {
                            "partner_id": self.partner_a.id,
                            "min_qty": 20,
                            "price": 10,
                            "discount": 15,
                        }
                    ),
                ],
            }
        )

        purchase_order = (
            self.env["purchase.order"]
            .with_company(self.company_data["company"])
            .create(
                {
                    "partner_id": self.partner_a.id,
                    "line_ids": [
                        Command.create(
                            {
                                "product_id": product.id,
                                "product_uom_id": product.uom_id.id,
                            }
                        )
                    ],
                }
            )
        )
        po_line = purchase_order.line_ids

        po_line.product_qty = 10
        self.assertEqual(
            po_line.discount,
            10,
            "first seller should be selected so discount should be 10",
        )
        self.assertEqual(
            po_line.price_subtotal, 90, "0.1 discount applied price should be 90"
        )

        po_line.product_qty = 22
        self.assertEqual(
            po_line.discount,
            15,
            "second seller should be selected so discount should be 15",
        )
        self.assertEqual(
            po_line.price_subtotal, 187, "0.15 discount applied price should be 187"
        )

        po_line.product_qty = 2
        self.assertEqual(
            po_line.discount, 0, "no seller should be selected so discount should be 0"
        )
        self.assertEqual(po_line.price_subtotal, 24, "No seller")

    def test_purchase_not_creating_useless_product_vendor(self):
        contact = self.env["res.partner"].create(
            {
                "name": "Contact",
                "type": "contact",
            }
        )

        delivery_address = self.env["res.partner"].create(
            {
                "name": "Delivery Address",
                "type": "delivery",
                "parent_id": contact.id,
            }
        )

        product = self.env["product.product"].create(
            {
                "name": "Product A",
                "seller_ids": [
                    (
                        0,
                        0,
                        {
                            "partner_id": delivery_address.id,
                            "min_qty": 1.0,
                            "price": 1.0,
                        },
                    )
                ],
            }
        )

        po_form = Form(self.env["purchase.order"])
        po_form.partner_id = delivery_address
        with po_form.line_ids.new() as po_line:
            po_line.product_id = product
            po_line.product_qty = 1.0
        po = po_form.save()
        po.action_confirm()

        self.assertEqual(
            po.line_ids.product_id.seller_ids.mapped("partner_id"), delivery_address
        )

    def test_supplier_list_in_product_with_multicompany(self):
        company_a = self.company_data["company"]
        company_b = self.company_data_2["company"]
        product = self.env["product.product"].create(
            {
                "name": "product_test",
            }
        )
        self.env["purchase.order"].with_company(company_a).create(
            {
                "partner_id": self.partner_a.id,
                "line_ids": [
                    (
                        0,
                        0,
                        {
                            "product_id": product.id,
                            "product_qty": 1,
                            "product_uom_id": self.env.ref("uom.product_uom_unit").id,
                            "price_unit": 1,
                        },
                    )
                ],
            }
        ).action_confirm()

        self.assertEqual(product.seller_ids[0].partner_id, self.partner_a)
        self.assertEqual(product.seller_ids[0].company_id, company_a)

        self.env["purchase.order"].with_company(company_b).create(
            {
                "partner_id": self.partner_b.id,
                "line_ids": [
                    (
                        0,
                        0,
                        {
                            "product_id": product.id,
                            "product_qty": 1,
                            "product_uom_id": self.env.ref("uom.product_uom_unit").id,
                            "price_unit": 2,
                        },
                    )
                ],
            }
        ).action_confirm()
        product = product.with_company(company_b)
        self.assertEqual(product.seller_ids[0].partner_id, self.partner_b)
        self.assertEqual(product.seller_ids[0].company_id, company_b)

        product = product.with_company(company_a)
        self.assertEqual(product.seller_ids[0].partner_id, self.partner_a)
        self.assertEqual(product.seller_ids[0].company_id, company_a)

        product._invalidate_cache()
        self.assertEqual(product.seller_ids[0].partner_id, self.partner_a)
        self.assertEqual(product.seller_ids[0].company_id, company_a)

    def test_discount_po_line_vendorpricelist(self):
        po = Form(self.env["purchase.order"])
        po.partner_id = self.partner_a
        with po.line_ids.new() as po_line:
            po_line.product_id = self.product_a
            po_line.product_qty = 1
            po_line.price_unit = 100
            po_line.discount = 20
        po = po.save()
        po.action_confirm()

        supplierinfo_id = self.env["product.supplierinfo"].search(
            [
                ("partner_id", "=", self.partner_a.id),
                ("product_tmpl_id", "=", self.product_a.product_tmpl_id.id),
            ],
            limit=1,
        )

        self.assertTrue(supplierinfo_id)
        self.assertEqual(supplierinfo_id.discount, 20)

        self.env["product.supplierinfo"].create(
            {
                "partner_id": self.partner_b.id,
                "product_tmpl_id": self.product_a.product_tmpl_id.id,
                "min_qty": 1,
                "price": 100,
                "discount": 30,
            }
        )

        po1 = Form(self.env["purchase.order"])
        po1.partner_id = self.partner_b
        with po1.line_ids.new() as po_line:
            po_line.product_id = self.product_a
            po_line.product_qty = 1
        po1 = po1.save()

        self.assertEqual(po1.line_ids[0].price_unit, 100)
        self.assertEqual(po1.line_ids[0].discount, 30)

    def test_orderline_supplierinfo_description(self):
        supplierinfo_vals = {
            "partner_id": self.partner_a.id,
            "min_qty": 1,
            "product_id": self.product_a.id,
            "product_tmpl_id": self.product_a.product_tmpl_id.id,
        }

        self.env["product.supplierinfo"].create(
            [
                {
                    **supplierinfo_vals,
                    "price": 10,
                    "product_name": "Name 1",
                    "product_code": "Code 1",
                },
                {
                    **supplierinfo_vals,
                    "price": 20,
                    "product_name": "Name 2",
                    "product_code": "Code 2",
                },
                {
                    "partner_id": self.partner_a.id,
                    "min_qty": 1,
                    "product_id": self.product_b.id,
                    "product_tmpl_id": self.product_b.product_tmpl_id.id,
                    "price": 5,
                    "product_name": "Name 3",
                    "product_code": "Code 3",
                },
            ]
        )

        po_form = Form(self.env["purchase.order"])
        po_form.partner_id = self.partner_a
        with po_form.line_ids.new() as line:
            line.product_id = self.product_a
            line.product_qty = 1
        po = po_form.save()
        self.assertEqual(po.line_ids.name, "[Code 1] Name 1")

        with po_form.line_ids.edit(0) as line:
            line.product_id = self.product_b
        po = po_form.save()
        self.assertEqual(po.line_ids.name, "[Code 3] Name 3")

    def test_purchase_order_line_product_taxes_on_branch(self):
        company = self.env.company
        branch_x = self.env["res.company"].create(
            {
                "name": "Branch X",
                "country_id": company.country_id.id,
                "parent_id": company.id,
            }
        )
        branch_xx = self.env["res.company"].create(
            {
                "name": "Branch XX",
                "country_id": company.country_id.id,
                "parent_id": branch_x.id,
            }
        )
        tax_groups = self.env["account.tax.group"].create(
            [
                {
                    "name": "Tax Group",
                    "company_ids": [Command.set(company.ids)],
                },
                {
                    "name": "Tax Group X",
                    "company_ids": [Command.set(branch_x.ids)],
                },
                {
                    "name": "Tax Group XX",
                    "company_ids": [Command.set(branch_xx.ids)],
                },
            ]
        )
        tax_a = self.env["account.tax"].create(
            {
                "name": "Tax A",
                "type_tax_use": "purchase",
                "amount_type": "percent",
                "amount": 10,
                "tax_group_id": tax_groups[0].id,
                "company_ids": [Command.set(company.ids)],
            }
        )
        tax_b = self.env["account.tax"].create(
            {
                "name": "Tax B",
                "type_tax_use": "purchase",
                "amount_type": "percent",
                "amount": 15,
                "tax_group_id": tax_groups[0].id,
                "company_ids": [Command.set(company.ids)],
            }
        )
        tax_x = self.env["account.tax"].create(
            {
                "name": "Tax X",
                "type_tax_use": "purchase",
                "amount_type": "percent",
                "amount": 20,
                "tax_group_id": tax_groups[1].id,
                "company_ids": [Command.set(branch_x.ids)],
            }
        )
        tax_xx = self.env["account.tax"].create(
            {
                "name": "Tax XX",
                "type_tax_use": "purchase",
                "amount_type": "percent",
                "amount": 25,
                "tax_group_id": tax_groups[2].id,
                "company_ids": [Command.set(branch_xx.ids)],
            }
        )
        product_all_taxes = self.env["product.product"].create(
            {
                "name": "Product all taxes",
                "supplier_taxes_id": [
                    Command.set((tax_a + tax_b + tax_x + tax_xx).ids)
                ],
            }
        )
        product_no_xx_tax = self.env["product.product"].create(
            {
                "name": "Product no tax from XX",
                "supplier_taxes_id": [Command.set((tax_a + tax_b + tax_x).ids)],
            }
        )
        product_no_branch_tax = self.env["product.product"].create(
            {
                "name": "Product no tax from branch",
                "supplier_taxes_id": [Command.set((tax_a + tax_b).ids)],
            }
        )
        product_no_tax = self.env["product.product"].create(
            {
                "name": "Product no tax",
                "supplier_taxes_id": [],
            }
        )
        po_form = Form(self.env["purchase.order"].with_company(branch_xx))
        po_form.partner_id = self.partner_a
        with po_form.line_ids.new() as line:
            line.product_id = product_all_taxes
        with po_form.line_ids.new() as line:
            line.product_id = product_no_xx_tax
        with po_form.line_ids.new() as line:
            line.product_id = product_no_branch_tax
        with po_form.line_ids.new() as line:
            line.product_id = product_no_tax
        po = po_form.save()
        self.assertRecordValues(
            po.line_ids,
            [
                {"product_id": product_all_taxes.id, "tax_ids": tax_xx.ids},
                {"product_id": product_no_xx_tax.id, "tax_ids": tax_x.ids},
                {
                    "product_id": product_no_branch_tax.id,
                    "tax_ids": (tax_a + tax_b).ids,
                },
                {"product_id": product_no_tax.id, "tax_ids": []},
            ],
        )

    @freeze_time("2024-07-08")
    def test_description_price__date_depending_on_vendor(self):
        self.product_a.seller_ids = [
            Command.create(
                {
                    "partner_id": self.partner_a.id,
                    "min_qty": 1,
                    "price": 5,
                    "product_code": "Vendor A",
                    "delay": 5,
                }
            ),
            Command.create(
                {
                    "partner_id": self.partner_b.id,
                    "min_qty": 1,
                    "price": 10,
                    "product_code": "Vendor B",
                    "delay": 6,
                }
            ),
        ]
        po_form = Form(self.env["purchase.order"])
        po_form.partner_id = self.partner_a
        with po_form.line_ids.new() as po_line:
            po_line.product_id = self.product_a
            po_line.product_qty = 10
        po = po_form.save()
        self.assertEqual(po.line_ids.price_unit, 5)
        self.assertEqual(po.line_ids.name, "[Vendor A] product_a")
        self.assertEqual(po.line_ids.product_qty, 10)
        self.assertEqual(
            po.line_ids.date_commitment, fields.Datetime.now() + timedelta(days=5)
        )
        po.partner_id = self.partner_b
        self.assertEqual(po.line_ids.price_unit, 10)
        self.assertEqual(po.line_ids.name, "[Vendor B] product_a")
        self.assertEqual(po.line_ids.product_qty, 10)
        self.assertEqual(
            po.line_ids.date_commitment, fields.Datetime.now() + timedelta(days=6)
        )

    def test_merge_purchase_order(self):
        PurchaseOrder = self.env["purchase.order"]
        user_1 = self.env["res.users"].search([])[0]
        user_2 = self.env["res.users"].search([])[1]
        payment_term_id_1 = self.env["account.payment.term"].search([])[0]
        payment_term_id_2 = self.env["account.payment.term"].search([])[1]

        po_1 = Form(PurchaseOrder)
        po_1.partner_id = self.partner_a
        po_1.partner_ref = "azure"
        po_1.origin = "s0003"
        po_1.user_id = user_1
        po_1.payment_term_id = payment_term_id_1
        with po_1.line_ids.new() as po_line:
            po_line.product_id = self.product_a
            po_line.product_qty = 1
            po_line.price_unit = 100
        with po_1.line_ids.new() as po_line:
            po_line.display_type = "line_note"
            po_line.name = "Test Note"
        po_1 = po_1.save()

        po_2 = Form(PurchaseOrder)
        po_2.partner_id = self.partner_a
        po_2.partner_ref = "wood corner"
        po_2.origin = "s0004"
        po_2.user_id = user_2
        po_2.payment_term_id = payment_term_id_2

        with po_2.line_ids.new() as po_line_1:
            po_line_1.product_id = self.product_a
            po_line_1.product_qty = 5
            po_line_1.price_unit = 100
        with po_2.line_ids.new() as po_line_2:
            po_line_2.product_id = self.product_b
            po_line_2.product_qty = 5
            po_line_2.price_unit = 500
        with po_2.line_ids.new() as po_line:
            po_line.display_type = "line_section"
            po_line.name = "Test section"
        po_2 = po_2.save()

        with self.assertRaises(UserError) as context:
            PurchaseOrder.browse([po_1.id]).action_merge()
        self.assertEqual(
            context.exception.args[0], "Please select at least two RFQs to merge."
        )

        selected_purchase_orders = po_1 | po_2
        selected_purchase_orders.action_merge()
        self.assertTrue(po_2.state == "cancel")
        self.assertEqual(po_1.line_ids[0].product_qty, 6)
        self.assertEqual(po_1.partner_ref, "azure, wood corner")
        self.assertEqual(po_1.origin, "s0003, s0004")
        self.assertEqual(po_1.user_id, user_1)
        self.assertEqual(po_1.payment_term_id, payment_term_id_1)

    def test_vendor_price_by_purchase_order_company(self):
        company_a = self.env.company
        company_b = self.env["res.company"].create({"name": "Saucisson Inc."})
        self.env = company_a.with_company(company_a).env

        self.product_a.write(
            {
                "seller_ids": [
                    Command.create(
                        {
                            "partner_id": self.partner_a,
                            "product_code": "A",
                            "company_id": company_a.id,
                            "price": 10.0,
                        }
                    ),
                    Command.create(
                        {
                            "partner_id": self.partner_a,
                            "product_code": "B",
                            "company_id": company_b.id,
                            "price": 15.0,
                        }
                    ),
                ]
            }
        )

        po = (
            self.env["purchase.order"]
            .with_context(allowed_company_ids=[company_a.id, company_b.id])
            .with_company(company_b)
            .create(
                {
                    "partner_id": self.partner_a.id,
                    "company_id": company_b.id,
                    "line_ids": [
                        Command.create(
                            {
                                "name": self.product_a.name,
                                "product_id": self.product_a.id,
                            }
                        )
                    ],
                }
            )
        )

        self.assertEqual(po.amount_untaxed, 15.0)
        po.company_id = company_a.id
        self.assertEqual(po.amount_untaxed, 10.0)

    def test_print_purchase_order_without_state_change(self):
        po_form = Form(self.env["purchase.order"])
        po_form.partner_id = self.partner_a
        with po_form.line_ids.new() as po_line:
            po_line.product_id = self.product
            po_line.product_qty = 1.0
        po = po_form.save()
        po.action_confirm()
        self.assertEqual(po.state, "done")
        report = self.env["ir.actions.report"]
        report._render_qweb_pdf("purchase.action_report_purchase_order", po.ids)
        self.assertEqual(po.state, "done")
        po.action_cancel()
        self.assertEqual(po.state, "cancel")
        report._render_qweb_pdf("purchase.report_purchase_quotation", po.ids)
        self.assertEqual(po.state, "cancel")
        self.assertEqual(po.count_print, 2)

    def test_purchase_warnings(self):
        partner_with_warning = self.env["res.partner"].create(
            {"name": "Test Partner", "purchase_warn_msg": "Highly infectious disease"}
        )
        child_partner = self.env["res.partner"].create(
            {
                "type": "invoice",
                "parent_id": partner_with_warning.id,
                "purchase_warn_msg": "Slightly infectious disease",
            }
        )
        purchase_order = self.env["purchase.order"].create(
            {"partner_id": partner_with_warning.id}
        )
        purchase_order2 = self.env["purchase.order"].create(
            {"partner_id": child_partner.id}
        )

        product_with_warning1 = self.env["product.product"].create(
            {"name": "Test Product 1", "purchase_line_warn_msg": "Highly corrosive"}
        )
        product_with_warning2 = self.env["product.product"].create(
            {"name": "Test Product 2", "purchase_line_warn_msg": "Toxic pollutant"}
        )
        self.env["purchase.order.line"].create(
            [
                {
                    "order_id": purchase_order.id,
                    "product_id": product_with_warning1.id,
                },
                {
                    "order_id": purchase_order.id,
                    "product_id": product_with_warning2.id,
                },
                {
                    "order_id": purchase_order.id,
                    "product_id": product_with_warning1.id,
                },
                {
                    "order_id": purchase_order2.id,
                    "product_id": product_with_warning2.id,
                },
            ]
        )
        group_warning_purchase = self.env.ref("purchase.group_warning_purchase")
        self.env.user.group_ids.implied_ids = [Command.link(group_warning_purchase.id)]
        purchase_order2.action_confirm()
        purchase_order2.create_invoice()
        invoice = Form(purchase_order2.invoice_ids[0])

        expected_warnings = (
            "Test Partner - Highly infectious disease",
            "Test Product 1 - Highly corrosive",
            "Test Product 2 - Toxic pollutant",
        )
        expected_warnings_for_purchase_order2 = (
            "Test Partner, Invoice - Slightly infectious disease",
            "Test Partner - Highly infectious disease",
            "Test Product 2 - Toxic pollutant",
        )
        self.assertEqual(
            purchase_order.purchase_warning_text, "\n".join(expected_warnings)
        )
        self.assertEqual(
            purchase_order2.purchase_warning_text,
            "\n".join(expected_warnings_for_purchase_order2),
        )
        self.assertEqual(
            invoice.purchase_warning_text,
            "\n".join(expected_warnings_for_purchase_order2),
        )

        self.env.user.group_ids.implied_ids = [
            Command.unlink(group_warning_purchase.id)
        ]
        self.assertEqual(purchase_order.purchase_warning_text, "")
        self.assertEqual(purchase_order2.purchase_warning_text, "")
        invoice = Form(purchase_order2.invoice_ids[0])
        self.assertEqual(invoice.purchase_warning_text, "")

    def test_bill_in_purchase_matching_individual(self):
        company_partner = self.env["res.partner"].create(
            {
                "name": "Small Company",
                "is_company": True,
            }
        )
        self.partner_a.parent_id = company_partner
        purchase_order = self.env["purchase.order"].create(
            {
                "partner_id": self.partner_a.id,
                "line_ids": [
                    (
                        0,
                        0,
                        {
                            "product_id": self.product_a.id,
                            "product_qty": 1,
                            "price_unit": 100,
                        },
                    )
                ],
            }
        )
        purchase_order.action_confirm()
        vendor_bill = self.env["account.move"].create(
            {
                "move_type": "in_invoice",
                "partner_id": self.partner_a.id,
                "invoice_line_ids": [
                    (
                        0,
                        0,
                        {
                            "product_id": self.product_a.id,
                            "quantity": 1,
                            "price_unit": 100,
                        },
                    )
                ],
            }
        )
        self.env["purchase.order"].flush_model()
        self.env["purchase.order.line"].flush_model()
        result = vendor_bill.action_purchase_matching()
        matching_records = self.env["purchase.bill.line.match"].search(result["domain"])
        result_bill_matching = purchase_order.action_bill_matching()
        matching_records_from_po = self.env["purchase.bill.line.match"].search(
            result_bill_matching["domain"]
        )

        matching_records.action_add_to_po()

        self.assertEqual(len(matching_records), 2)
        self.assertEqual(matching_records.account_move_id, vendor_bill)
        self.assertEqual(matching_records.order_id, purchase_order)
        self.assertEqual(len(matching_records_from_po), 2)
        self.assertEqual(matching_records_from_po.account_move_id, vendor_bill)
        self.assertEqual(matching_records_from_po.order_id, purchase_order)

    def test_purchase_suggest_qty(self):
        self.env["product.supplierinfo"].create(
            [
                {
                    "partner_id": self.partner_a.id,
                    "product_id": self.product_a.id,
                    "min_qty": 1,
                    "price": 50,
                    "date_start": fields.Date.today() - timedelta(days=5),
                    "date_end": fields.Date.today() - timedelta(days=3),
                    "product_code": "product_code_1",
                },
                {
                    "partner_id": self.partner_a.id,
                    "product_id": self.product_a.id,
                    "min_qty": 10,
                    "price": 100,
                    "date_start": fields.Date.today() - timedelta(days=5),
                    "date_end": fields.Date.today() + timedelta(days=3),
                    "product_code": "HHH",
                },
                {
                    "partner_id": self.partner_a.id,
                    "product_id": self.product_a.id,
                    "min_qty": 20,
                    "price": 80,
                    "date_start": fields.Date.today() - timedelta(days=5),
                    "date_end": fields.Date.today() + timedelta(days=3),
                    "product_code": "HHH-min_qty_20",
                },
            ]
        )
        po_form = Form(self.env["purchase.order"])
        po_form.partner_id = self.partner_a
        with po_form.line_ids.new() as po_line:
            po_line.product_id = self.product_a
        po = po_form.save()
        self.assertEqual(po.line_ids.product_qty, 10.0)
        self.assertEqual(po.line_ids.name, "[HHH] product_a")

    def test_purchase_order_uom(self):
        fuzzy_drink = self.env["product.product"].create(
            {
                "name": "Fuzzy Drink",
                "uom_id": self.env.ref("uom.product_uom_unit").id,
                "seller_ids": [
                    Command.create(
                        {
                            "partner_id": self.partner_a.id,
                            "product_uom_id": self.env.ref("uom.product_uom_unit").id,
                            "price": 1,
                        }
                    ),
                    Command.create(
                        {
                            "partner_id": self.partner_a.id,
                            "product_uom_id": self.env.ref("uom.product_uom_pack_6").id,
                            "min_qty": 2,
                            "price": 5,
                        }
                    ),
                ],
            }
        )

        po = self.env["purchase.order"].create(
            {
                "partner_id": self.partner_a.id,
                "line_ids": [
                    Command.create(
                        {
                            "product_id": fuzzy_drink.id,
                            "product_qty": 15,
                            "product_uom_id": self.env.ref("uom.product_uom_unit").id,
                        }
                    )
                ],
            }
        )
        self.assertEqual(po.line_ids.price_unit, 1)
        po.line_ids.product_qty = 1
        po.line_ids.product_uom_id = self.env.ref("uom.product_uom_pack_6")
        self.assertEqual(po.line_ids.price_unit, 6)
        po.line_ids.product_qty = 2
        self.assertEqual(po.line_ids.price_unit, 5)

    def test_purchase_order_lock(self):
        po = self.env["purchase.order"].create(
            {
                "partner_id": self.partner_a.id,
                "line_ids": [
                    Command.create(
                        {
                            "product_id": self.product_a.id,
                        }
                    )
                ],
            }
        )
        po.action_confirm()
        self.assertFalse(po.locked)
        po.action_lock()
        self.assertTrue(po.locked)
        self.assertNotEqual(po.company_id.order_lock_po, "lock")
        po.action_unlock()
        self.assertFalse(po.locked)

        po.action_lock()
        self.assertTrue(po.locked)
        po.company_id.order_lock_po = "lock"
        po.action_unlock()
        self.assertFalse(po.locked)

    def test_purchase_order_mail_links_to_correct_website(self):
        if "website_id" not in self.env.company:
            self.skipTest(
                "The `website` module is required to support multiple company websites."
            )

        company1 = self.company_data["company"]
        company2 = self.company_data_2["company"]
        companies = company1 + company2
        companies.website_id = None
        self.env["website"].create(
            [
                {
                    "name": f"{company.name}'s Website",
                    "domain": f"http://website{company.id}.example.com",
                    "company_id": company.id,
                }
                for company in companies
            ]
        )
        self.assertEqual(len(companies.website_id), 2)

        rfq = self.env["purchase.order"].create(
            {
                "partner_id": self.partner_a.id,
                "company_id": company2.id,
                "line_ids": [Command.create({"product_id": self.product_a.id})],
            }
        )

        email_ctx = rfq.action_send_rfq().get("context", {})
        mail_template = self.env["mail.template"].browse(
            email_ctx.get("default_template_id")
        )
        mail_template.auto_delete = False

        message = rfq.with_context(**email_ctx).message_post_with_source(
            mail_template,
            subtype_xmlid="mail.mt_comment",
        )
        self.assertIn(
            company2.website_id.domain,
            message.mail_ids.body_html,
            "Mail should link to the website of the order's company",
        )
        self.assertNotIn(
            company1.website_id.domain,
            message.mail_ids.body_html,
            "Mail shouldn't link to the website of the first company",
        )
        self.assertNotIn(
            self.env["base"].get_base_url(),
            message.mail_ids.body_html,
            "Mail shouldn't link to the base URL",
        )

    def test_action_view_po_when_product_template_archived(self):
        po = self.env["purchase.order"].create(
            {
                "partner_id": self.partner_a.id,
                "line_ids": [
                    Command.create(
                        {
                            "product_id": self.product_a.id,
                            "product_qty": 10,
                            "price_unit": 1,
                        }
                    ),
                ],
            }
        )
        po.action_confirm()
        product_tmpl = self.product_a.product_tmpl_id
        self.assertEqual(product_tmpl.purchased_product_qty, 10)

        product_tmpl.active = False
        product_tmpl.invalidate_recordset()

        self.assertEqual(product_tmpl.purchased_product_qty, 10)

        action = product_tmpl.action_view_po()
        action_record = self.env[action["res_model"]].search(action["domain"])
        self.assertEqual(action_record, po.line_ids)

    def test_currency_computed_from_partner(self):
        eur = self.env.ref("base.EUR")
        gbp = self.env.ref("base.GBP")
        self.partner_a.property_purchase_currency_id = eur
        po = self.env["purchase.order"].create(
            {
                "partner_id": self.partner_a.id,
            }
        )
        self.assertEqual(
            po.currency_id,
            eur,
            "The currency should be computed from the partner's purchase currency",
        )
        po_2 = (
            self.env["purchase.order"]
            .with_context(default_currency_id=gbp)
            .create(
                {
                    "partner_id": self.partner_a.id,
                }
            )
        )
        self.assertEqual(
            po_2.currency_id,
            gbp,
            "The currency should be set from context default_currency_id, bypassing the compute",
        )

    def test_prevent_recompute_price_on_manual_set(self):
        self.product_a.seller_ids = [
            Command.create(
                {
                    "partner_id": self.partner_a.id,
                    "min_qty": 1,
                    "price": 5,
                    "product_code": "Vendor A",
                }
            )
        ]
        po_form = Form(self.env["purchase.order"])
        po_form.partner_id = self.partner_a
        with po_form.line_ids.new() as po_line:
            po_line.product_id = self.product_a
            po_line.product_qty = 1
        po = po_form.save()
        self.assertEqual(po.line_ids.price_unit, 5)
        with Form(po.line_ids) as line:
            line.price_unit = 100.0
        po.line_ids.product_qty = 10
        self.assertEqual(
            po.line_ids.price_unit,
            100.0,
            "Price should remain 100.0 after changing the quantity",
        )

    def test_purchase_order_line_without_uom(self):
        uom_test = self.env["uom.uom"].create(
            {
                "name": "Test Uom",
                "rounding": 1.0,
            }
        )

        po = self.env["purchase.order"].create(
            {
                "partner_id": self.partner_a.id,
                "line_ids": [
                    (
                        0,
                        0,
                        {
                            "product_id": self.product_a.id,
                            "product_qty": 1.0,
                            "product_uom_id": uom_test.id,
                        },
                    )
                ],
            }
        )

        with (
            self.assertRaises(IntegrityError),
            self.cr.savepoint(),
            mute_logger("odoo.db"),
        ):
            uom_test.unlink()

        self.assertEqual(po.line_ids[0].product_uom_id, uom_test)

    def test_locked_purchase_order_cannot_cancel(self):
        po = self.env["purchase.order"].create(
            {
                "partner_id": self.partner_a.id,
                "line_ids": [
                    Command.create(
                        {
                            "product_id": self.product_a.id,
                            "product_qty": 1.0,
                        }
                    ),
                ],
            }
        )
        po.action_confirm()
        self.assertFalse(po.locked)
        po.action_lock()
        self.assertTrue(po.locked, "The purchase order should be locked.")

        with self.assertRaises(UserError):
            po.action_cancel()

        po.action_unlock()
        po.action_cancel()
        self.assertEqual(po.state, "cancel", "The purchase order should be cancelled.")
