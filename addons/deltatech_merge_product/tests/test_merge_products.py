# ©  2008-2021 Deltatech
#              Dorin Hongu <dhongu(@)gmail(.)com
# See README.rst file on addons root folder for license details


from odoo.tests import Form, tagged
from odoo.tests.common import TransactionCase


@tagged("post_install", "-at_install")
class TestInvoiceReceipt(TransactionCase):
    def setUp(self):
        super().setUp()
        self.partner_a = self.env["res.partner"].create({"name": "Test"})

        self.uom_unit = self.env.ref("uom.product_uom_unit")

        seller_ids = [(0, 0, {"partner_id": self.partner_a.id})]

        self.product_a = self.env["product.product"].create(
            {
                "name": "Test A",
                "uom_id": self.uom_unit.id,
                "uom_po_id": self.uom_unit.id,
                "standard_price": 100,
                "list_price": 150,
                "seller_ids": seller_ids,
            }
        )
        self.product_b = self.env["product.product"].create(
            {
                "name": "Test B",
                "uom_id": self.uom_unit.id,
                "uom_po_id": self.uom_unit.id,
                "standard_price": 100,
                "list_price": 150,
                "seller_ids": seller_ids,
            }
        )

        self.product_c = self.env["product.template"].create(
            {
                "name": "Test A",
                "uom_id": self.uom_unit.id,
                "uom_po_id": self.uom_unit.id,
                "standard_price": 100,
                "list_price": 150,
                "seller_ids": seller_ids,
            }
        )
        self.product_d = self.env["product.template"].create(
            {
                "name": "Test B",
                "uom_id": self.uom_unit.id,
                "uom_po_id": self.uom_unit.id,
                "standard_price": 100,
                "list_price": 150,
                "seller_ids": seller_ids,
            }
        )

    def test_merge_products(self):
        products = self.env["product.product"]

        products |= self.product_a
        products |= self.product_b
        form_merge_wizard = Form(
            self.env["merge.product.wizard"].with_context(
                {
                    "active_model": "product.product",
                    "active_id": self.product_a.id,
                    "active_ids": products.ids,
                }
            )
        )
        merge_wizard = form_merge_wizard.save()
        merge_wizard.action_merge()

    def test_merge_templates(self):
        products = self.env["product.template"]

        products |= self.product_c
        products |= self.product_d
        form_merge_wizard = Form(
            self.env["merge.product.wizard"].with_context(
                {
                    "active_model": "product.template",
                    "active_id": self.product_c.id,
                    "active_ids": products.ids,
                }
            )
        )
        merge_wizard = form_merge_wizard.save()
        merge_wizard.action_merge()
