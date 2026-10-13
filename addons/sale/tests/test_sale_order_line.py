# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.fields import Command

from odoo.addons.sale.tests.common import SaleCommon


class TestSaleOrderLine(SaleCommon):
    # Those tests do not rely on accounting common on purpose
    #   If you need the accounting setup, use other classes (TestSaleToInvoice probably)

    def test_sale_order_line_description(self):
        self.product.sudo().description_sale = "Description"
        self.sale_order.order_line = [
            Command.clear(),
            Command.create({"product_id": self.product.id}),
            Command.create({"product_id": self.product.id, "name": "Description"}),
            Command.create({
                "product_id": self.product.id,
                "name": "Test Product\nManual Description",
            }),
            # Through `_inverse_label`
            Command.create({"product_id": self.product.id, "label": "Test Product\nDescription"}),
            Command.create({"product_id": self.product.id, "label": "Description"}),
            Command.create({"label": "Manual Description"}),
        ]

        # Force the invalidation to ensure the label is recomputed based on the saved values
        # otherwise the value provided will be used even though its dependencies changed
        self.sale_order.order_line.invalidate_recordset(["label"])

        self.assertRecordValues(
            self.sale_order.order_line,
            [
                {
                    "product_id": self.product.id,
                    "name": "Description",
                    "label": "Test Product\nDescription",
                    "display_name": f"{self.sale_order.name} - Test Product ({self.partner.name})",
                },
                {
                    "product_id": self.product.id,
                    "name": "Description",
                    "label": "Test Product\nDescription",
                    "display_name": f"{self.sale_order.name} - Test Product ({self.partner.name})",
                },
                # `name` and `label` are identical when the product name is already part of the
                # description. This can happen with SOs created before v20, when the product name
                # was included in the description.
                {
                    "product_id": self.product.id,
                    "name": "Test Product\nManual Description",
                    "label": "Test Product\nManual Description",
                    "display_name": f"{self.sale_order.name} - Test Product ({self.partner.name})",
                },
                # Through `_inverse_label`
                {
                    "product_id": self.product.id,
                    "name": "Description",
                    "label": "Test Product\nDescription",
                    "display_name": f"{self.sale_order.name} - Test Product ({self.partner.name})",
                },
                {
                    "product_id": self.product.id,
                    "name": "Description",
                    "label": "Test Product\nDescription",
                    "display_name": f"{self.sale_order.name} - Test Product ({self.partner.name})",
                },
                {
                    "product_id": False,
                    "name": "Manual Description",
                    "label": "Manual Description",
                    "display_name": f"{self.sale_order.name} - Manual Description ({self.partner.name})",  # noqa: E501
                },
            ],
        )

    def test_sale_order_line_description_skips_empty_custom_value(self):
        engraving_attribute = self.env["product.attribute"].sudo().create({
            "name": "Engraving",
            "create_variant": "no_variant",
            "value_ids": [
                Command.create({"name": "Initials"}),
                Command.create({"name": "Custom", "is_custom": True}),
            ],
        })
        self.product.sudo().description_sale = "Description"
        product_template = self.product.product_tmpl_id.sudo()
        product_template.attribute_line_ids = [
            Command.create({
                "attribute_id": engraving_attribute.id,
                "value_ids": [Command.set(engraving_attribute.value_ids.ids)],
            })
        ]
        custom_ptav = product_template.attribute_line_ids.product_template_value_ids.filtered(
            "is_custom"
        )

        self.sale_order.order_line = [
            Command.clear(),
            Command.create({
                "product_id": self.product.id,
                "product_no_variant_attribute_value_ids": [Command.set(custom_ptav.ids)],
            }),
        ]

        self.assertEqual(self.sale_order.order_line.name, "Description")
