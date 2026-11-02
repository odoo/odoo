from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestBillingRequestLine(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.product = cls.env["product.product"].create(
            {"name": "BR Service", "type": "service", "list_price": 100.0}
        )

    def test_add_line_to_request(self):
        request = self.env["od19.billing.request"].create(
            {
                "direction": "ar",
                "line_ids": [
                    (
                        0,
                        0,
                        {
                            "product_id": self.product.id,
                            "name": "BR Service",
                            "quantity": 2.0,
                            "price_unit": 100.0,
                        },
                    )
                ],
            }
        )
        self.assertEqual(len(request.line_ids), 1)
        line = request.line_ids
        self.assertEqual(line.request_id, request)
        self.assertEqual(line.quantity, 2.0)
