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
