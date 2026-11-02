from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestBillingRequestAcl(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.product = cls.env["product.product"].create(
            {"name": "BR ACL Widget", "type": "consu", "list_price": 10.0}
        )
        cls.requester = cls.env["res.users"].create(
            {
                "name": "BR Requester",
                "login": "br_requester_acl",
                "email": "br_requester_acl@example.com",
                "group_ids": [
                    (
                        6,
                        0,
                        [
                            cls.env.ref("base.group_user").id,
                            cls.env.ref(
                                "od19_billing_request.group_od19_billing_requester"
                            ).id,
                        ],
                    )
                ],
            }
        )

    def test_requester_can_create_and_read_request_line(self):
        request = (
            self.env["od19.billing.request"]
            .with_user(self.requester)
            .create(
                {
                    "direction": "ar",
                    "line_ids": [
                        (
                            0,
                            0,
                            {
                                "product_id": self.product.id,
                                "name": "BR ACL Widget",
                                "quantity": 1.0,
                                "price_unit": 10.0,
                            },
                        )
                    ],
                }
            )
        )
        line = request.with_user(self.requester).line_ids
        self.assertEqual(len(line), 1)
        self.assertEqual(line.quantity, 1.0)

    def test_requester_can_read_pull_sources(self):
        """The pull wizard reads sources in the requester's own context."""
        for model_name in (
            "sale.order",
            "sale.order.line",
            "purchase.order",
            "purchase.order.line",
            "stock.picking",
            "stock.move",
        ):
            self.assertTrue(
                self.env[model_name]
                .with_user(self.requester)
                .check_access_rights("read", raise_exception=False),
                "requester should have read access to %s" % model_name,
            )

    def test_requester_has_read_only_on_pull_sources(self):
        """Read access must not silently grant write on the sources."""
        self.assertFalse(
            self.env["sale.order"]
            .with_user(self.requester)
            .check_access_rights("write", raise_exception=False)
        )
