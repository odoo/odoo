# Copyright 2017 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo.tests import tagged

from .common import TestCommon


@tagged("post_install", "-at_install")
class TestMultiCompany(TestCommon):
    @classmethod
    def create_company(cls, values):
        return cls.env["res.company"].create(values)

    @classmethod
    def create_product(cls, values):
        values.update({"type": "consu", "invoice_policy": "order"})
        product_template = cls.env["product.template"].create(values)
        return product_template.product_variant_id

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(
            context=dict(
                cls.env.context,
                tracking_disable=True,
                # Compatibility with sale_automatic_workflow_job: even if
                # the module is installed, ensure we don't delay a job.
                # Thus, we test the usual flow.
                queue_job__no_delay=True,
            )
        )
        coa = cls.env.user.company_id.chart_template_id
        cls.company_fr = cls.create_company(
            {
                "name": "French company",
                "currency_id": cls.env.ref("base.EUR").id,
                "country_id": cls.env.ref("base.fr").id,
            }
        )

        cls.company_ch = cls.create_company(
            {
                "name": "Swiss company",
                "currency_id": cls.env.ref("base.CHF").id,
                "country_id": cls.env.ref("base.ch").id,
            }
        )

        cls.company_be = cls.create_company(
            {
                "name": "Belgian company",
                "currency_id": cls.env.ref("base.EUR").id,
                "country_id": cls.env.ref("base.be").id,
            }
        )

        cls.company_fr_daughter = cls.create_company(
            {
                "name": "French company daughter",
                "currency_id": cls.env.ref("base.EUR").id,
                "country_id": cls.env.ref("base.fr").id,
            }
        )

        cls.env.user.company_ids |= cls.company_fr
        cls.env.user.company_ids |= cls.company_ch
        cls.env.user.company_ids |= cls.company_be
        cls.env.user.company_ids |= cls.company_fr_daughter

        cls.env.user.company_id = cls.company_fr.id
        coa.try_loading(company=cls.env.user.company_id)
        cls.customer_fr = (
            cls.env["res.partner"]
            .with_context(default_company_id=cls.company_fr.id)
            .create({"name": "Customer FR", "email": "test_fr@example.com"})
        )
        cls.product_fr = cls.create_product({"name": "Evian bottle", "list_price": 2.0})

        cls.env.user.company_id = cls.company_ch.id
        coa.try_loading(company=cls.env.user.company_id)
        cls.customer_ch = cls.env["res.partner"].create(
            {"name": "Customer CH", "email": "test_ch@example.com"}
        )
        cls.product_ch = cls.create_product(
            {"name": "Henniez bottle", "list_price": 3.0}
        )

        cls.env.user.company_id = cls.company_be.id
        coa.try_loading(company=cls.env.user.company_id)
        cls.customer_be = cls.env["res.partner"].create(
            {"name": "Customer BE", "email": "test_be@example.com"}
        )
        cls.product_be = (
            cls.env["product.template"]
            .create(
                {
                    "name": "SPA bottle",
                    "list_price": 1.5,
                    "type": "consu",
                    "invoice_policy": "order",
                }
            )
            .product_variant_id
        )

        cls.env.user.company_id = cls.company_fr_daughter.id
        coa.try_loading(company=cls.env.user.company_id)
        cls.customer_fr_daughter = cls.env["res.partner"].create(
            {"name": "Customer FR Daughter", "email": "test_daughter_fr@example.com"}
        )
        cls.product_fr_daughter = cls.create_product(
            {"name": "Contrex bottle", "list_price": 1.5}
        )

        cls.auto_wkf = cls.env.ref("sale_automatic_workflow.automatic_validation")
        cls.auto_wkf.validate_picking = True
        cls.env.user.company_id = cls.env.ref("base.main_company")

    def create_auto_wkf_order(self, company, customer, product, qty):
        # We need to change to the proper company
        # to pick up correct company dependent fields
        SaleOrder = self.env["sale.order"].with_company(company)
        warehouse = self.env["stock.warehouse"].search(
            [("company_id", "=", company.id)], limit=1
        )

        self.product_uom_unit = self.env.ref("uom.product_uom_unit")

        order = SaleOrder.create(
            {
                "partner_id": customer.id,
                "company_id": company.id,
                "warehouse_id": warehouse.id,
                "workflow_process_id": self.auto_wkf.id,
                "order_line": [
                    (
                        0,
                        0,
                        {
                            "name": product.name,
                            "product_id": product.id,
                            "price_unit": product.list_price,
                            "product_uom_qty": qty,
                            "product_uom": self.product_uom_unit.id,
                        },
                    )
                ],
            }
        )
        order._onchange_workflow_process_id()
        return order

    def test_sale_order_multicompany(self):

        self.env.user.company_id = self.env.ref("base.main_company")
        order_fr = self.create_auto_wkf_order(
            self.company_fr, self.customer_fr, self.product_fr, 5
        )
        order_ch = self.create_auto_wkf_order(
            self.company_ch, self.customer_ch, self.product_ch, 10
        )
        order_be = self.create_auto_wkf_order(
            self.company_be, self.customer_be, self.product_be, 10
        )
        order_fr_daughter = self.create_auto_wkf_order(
            self.company_fr_daughter,
            self.customer_fr_daughter,
            self.product_fr_daughter,
            4,
        )

        self.assertEqual(order_fr.state, "draft")
        self.assertEqual(order_ch.state, "draft")
        self.assertEqual(order_be.state, "draft")
        self.assertEqual(order_fr_daughter.state, "draft")

        self.env["automatic.workflow.job"].run()
        self.assertTrue(order_fr.picking_ids)
        self.assertTrue(order_ch.picking_ids)
        self.assertTrue(order_be.picking_ids)
        self.assertEqual(order_fr.picking_ids.state, "done")
        self.assertEqual(order_ch.picking_ids.state, "done")
        self.assertEqual(order_be.picking_ids.state, "done")
        invoice_fr = order_fr.invoice_ids
        invoice_ch = order_ch.invoice_ids
        invoice_be = order_be.invoice_ids
        invoice_fr_daughter = order_fr_daughter.invoice_ids
        self.assertEqual(invoice_fr.state, "posted")
        self.assertEqual(invoice_fr.journal_id.company_id, order_fr.company_id)
        self.assertEqual(invoice_ch.state, "posted")
        self.assertEqual(invoice_ch.journal_id.company_id, order_ch.company_id)
        self.assertEqual(invoice_be.state, "posted")
        self.assertEqual(invoice_be.journal_id.company_id, order_be.company_id)
        self.assertEqual(invoice_fr_daughter.state, "posted")
        self.assertEqual(
            invoice_fr_daughter.journal_id.company_id, order_fr_daughter.company_id
        )
