from odoo.fields import Command
from odoo.tests import HttpCase, tagged

from odoo.addons.sale.tests.common import SaleOrderTemplateCommon


@tagged("post_install", "-at_install")
class TestPortalQuoteOptionUpdate(HttpCase, SaleOrderTemplateCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.sale_order_with_option = cls.env["sale.order"].create(
            {
                "partner_id": cls.partner.id,
                "line_ids": [
                    Command.create(
                        {
                            "display_type": "line_section",
                            "name": "Optional products",
                            "is_optional": True,
                        }
                    ),
                    Command.create(
                        {
                            "product_id": cls.product.id,
                        }
                    ),
                ],
            }
        )
        cls.sale_order_with_option._portal_get_or_create_token()
        cls.optional_line = cls._get_optional_product_lines(cls.sale_order_with_option)

    def test_negative_input_quantity_is_clamped_to_zero(self):
        self.authenticate(None, None)

        self.call_jsonrpc(
            f"/my/orders/{self.sale_order_with_option.id}/update_line_dict",
            {
                "access_token": self.sale_order_with_option.access_token,
                "line_id": self.optional_line.id,
                "input_quantity": -5,
            },
        )

        self.assertEqual(
            self.optional_line.product_qty,
            0,
            "a negative input_quantity must be clamped to 0, never applied as-is",
        )
