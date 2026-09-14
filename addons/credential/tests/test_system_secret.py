from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestSystemSecret(TransactionCase):
    def test_a_system_secret_round_trips_encrypted_and_leaves_no_parameter(self):
        Credential = self.env["credential.credential"]

        Credential._set_system_secret("probe_client_secret", "s3cr3t")

        self.assertEqual(Credential._get_system_secret("probe_client_secret"), "s3cr3t")
        credential = Credential._get_system_secret_credential("probe_client_secret")
        self.assertFalse(credential.company_id)
        self.assertTrue(credential.credential_value_encrypted)
        self.assertFalse(
            self.env["ir.config_parameter"].sudo().get_param("probe_client_secret")
        )

    def test_writing_it_again_replaces_it_and_clearing_it_removes_it(self):
        Credential = self.env["credential.credential"]
        Credential._set_system_secret("probe_client_secret", "first")

        Credential._set_system_secret("probe_client_secret", "second")
        self.assertEqual(Credential._get_system_secret("probe_client_secret"), "second")

        Credential._set_system_secret("probe_client_secret", False)
        self.assertFalse(Credential._get_system_secret("probe_client_secret"))
        self.assertFalse(
            Credential._get_system_secret_credential("probe_client_secret")
        )

    def test_presence_is_known_without_the_value(self):
        Credential = self.env["credential.credential"]
        self.assertFalse(Credential._has_system_secret("probe_client_secret"))

        Credential._set_system_secret("probe_client_secret", "s3cr3t")

        self.assertTrue(Credential._has_system_secret("probe_client_secret"))

    def test_parameters_move_into_system_secrets_and_their_rows_go(self):
        Credential = self.env["credential.credential"]
        parameters = self.env["ir.config_parameter"].sudo()
        parameters.set_param("probe.api_key", "k3y")
        parameters.create({"key": "probe.empty_key", "value": ""})

        moved = Credential._move_parameters_into_system_secrets(
            ["probe.api_key", "probe.empty_key"]
        )

        self.assertEqual(moved, 1)
        self.assertEqual(Credential._get_system_secret("probe.api_key"), "k3y")
        self.assertFalse(
            parameters.search([("key", "in", ["probe.api_key", "probe.empty_key"])])
        )
