from odoo.exceptions import ValidationError
from odoo.tests import TransactionCase, tagged
from odoo.tools import mute_logger

from odoo.addons.mixin_encryption.tests.common import EncryptionKeyCase


@tagged("post_install", "-at_install")
class TestAccessLogOutcome(EncryptionKeyCase, TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.category = cls.env.ref("credential.credential_category_api_key")

    def _credential(self, name, cap=2):
        credential = self.env["credential.credential"].create(
            {
                "name": name,
                "category_id": self.category.id,
                "credential_value": "PLAINTEXT",
            }
        )
        credential.sudo().write(
            {"decrypt_rate_limit_enabled": True, "decrypt_rate_limit_max": cap}
        )
        self.env.flush_all()
        return credential

    def test_a_granted_operation_is_recorded_as_a_success(self):
        vals = self._credential("outcome granted")._prepare_access_log_vals(
            "read", False
        )
        self.assertIs(vals["success"], True)
        self.assertNotIn("failure_reason", vals)

    def test_a_denied_operation_is_recorded_as_a_failure(self):
        vals = self._credential("outcome denied")._prepare_access_log_vals(
            "read_rate_limited", False
        )
        self.assertIs(vals["success"], False)
        self.assertTrue(
            vals["failure_reason"],
            "the row that records a refusal has to say what refused it",
        )

    def test_the_vocabulary_is_the_log_model_s_own(self):
        denied = self.env["credential.access.log"].DENIED_OPERATIONS
        operations = dict(
            self.env["credential.access.log"]._fields["operation"].selection
        )
        self.assertTrue(denied, "at least one operation records a refusal")
        self.assertLessEqual(
            set(denied),
            set(operations),
            "every denied operation must be a real 'operation' value",
        )

    @mute_logger("odoo.addons.credential.models.credential_credential")
    def test_the_audited_row_of_a_real_denial(self):
        registry = self.env.registry
        with registry.cursor() as cr:
            env = self.env(cr=cr)
            credential = env["credential.credential"].create(
                {
                    "name": "outcome audited",
                    "category_id": self.category.id,
                    "credential_value": "PLAINTEXT",
                }
            )
            credential.sudo().write(
                {"decrypt_rate_limit_enabled": True, "decrypt_rate_limit_max": 1}
            )
            credential_id = credential.id
            cr.commit()

        try:
            with registry.cursor() as cr:
                env = self.env(cr=cr)
                credential = env["credential.credential"].browse(credential_id)
                credential.invalidate_recordset(
                    ["cached_plaintext", "credential_value"]
                )
                self.assertEqual(credential.credential_value, "PLAINTEXT")
                credential.invalidate_recordset(
                    ["cached_plaintext", "credential_value"]
                )
                with self.assertRaises(ValidationError):
                    _ = credential.credential_value
                cr.commit()

            with registry.cursor() as cr:
                env = self.env(cr=cr)
                logs = (
                    env["credential.access.log"]
                    .sudo()
                    .search([("credential_id", "=", credential_id)])
                )
                denials = logs.filtered(
                    lambda log: log.operation == "read_rate_limited"
                )
                grants = logs.filtered(lambda log: log.operation == "read")
                self.assertTrue(denials, "the refusal was audited")
                self.assertTrue(grants, "the granted read was audited too")
                self.assertFalse(
                    any(denials.mapped("success")),
                    "a refused decryption must not be stored as a success",
                )
                self.assertTrue(
                    all(denials.mapped("failure_reason")),
                    "and it must carry the reason the form view renders",
                )
                self.assertTrue(all(grants.mapped("success")))
        finally:
            with registry.cursor() as cr:
                env = self.env(cr=cr)
                env["credential.access.log"].sudo().search(
                    [("credential_id", "=", credential_id)]
                ).with_context(_credential_log_cleanup_bypass=True).unlink()
                env["credential.credential"].browse(credential_id).sudo().unlink()
                cr.commit()
