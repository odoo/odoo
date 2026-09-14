from odoo.tests import TransactionCase, new_test_user, tagged


@tagged("post_install", "-at_install")
class TestGloryCredentials(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.method = cls.env["pos.payment.method"].create(
            {"name": "Glory", "glory_username": "cashier", "glory_password": "pw"}
        )

    def test_the_password_lives_in_the_methods_credential(self):
        self.method.invalidate_recordset()

        self.assertFalse(self.env["pos.payment.method"]._fields["glory_password"].store)
        self.assertEqual(self.method.glory_password, "pw")
        self.assertEqual(
            self.method.terminal_credential_id._use_secret_payload(
                "pos:payment_method"
            ),
            {"glory_password": "pw"},
        )

    def test_a_copy_holds_its_own_credential(self):
        copy = self.method.copy()

        self.assertEqual(copy.glory_password, "pw")
        self.assertNotEqual(
            copy.terminal_credential_id, self.method.terminal_credential_id
        )

    def test_a_pos_user_reads_the_password_the_pos_loads(self):
        cashier = new_test_user(
            self.env, "glory_cashier", groups="point_of_sale.group_pos_user"
        )

        self.assertIn("glory_password", self.method._load_pos_data_fields(None))
        self.assertEqual(
            self.method.with_user(cashier).read(["glory_password"])[0][
                "glory_password"
            ],
            "pw",
        )
