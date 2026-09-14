from odoo.tests import TransactionCase, tagged
from odoo.tools import mute_logger


class CredentialUnlinkCommon(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.category = cls.env.ref("credential.credential_category_api_key")

    def _make_credential(self, name, **vals):
        return self.env["credential.credential"].create(
            {
                "name": name,
                "category_id": self.category.id,
                "api_key": "SECRET",
                **vals,
            }
        )

    def _delete_rows(self, name):
        return (
            self.env["credential.access.log"]
            .sudo()
            .search([("operation", "=", "delete"), ("credential_name", "=", name)])
        )


@tagged("post_install", "-at_install")
class TestCredentialUnlinkAudit(CredentialUnlinkCommon):
    def test_delete_writes_exactly_one_readable_audit_row(self):
        credential = self._make_credential("unlink audit")
        credential.unlink()

        rows = self._delete_rows("unlink audit")
        self.assertEqual(
            len(rows),
            1,
            "one deletion must leave exactly one delete audit row",
        )
        self.assertEqual(rows.credential_name, "unlink audit")
        self.assertEqual(rows.user_login, self.env.user.login)
        self.assertFalse(
            rows.credential_id,
            "the FK is deliberately not set: the row it would point at is gone, "
            "and setting it is what used to break the delete",
        )

    def test_bulk_delete_writes_one_row_each(self):
        names = ["bulk a", "bulk b", "bulk c"]
        credentials = self.env["credential.credential"]
        for name in names:
            credentials |= self._make_credential(name)

        credentials.unlink()

        for name in names:
            self.assertEqual(len(self._delete_rows(name)), 1, name)

    def test_audit_row_survives_a_reader_that_never_knew_the_credential(self):
        credential = self._make_credential("readable after delete")
        credential.unlink()

        row = self._delete_rows("readable after delete")
        self.assertNotIn(
            "(deleted)",
            row.display_name,
            "denormalized credential_name must keep the row readable",
        )

    @mute_logger("odoo.addons.credential.models.credential_credential")
    def test_a_failing_audit_write_does_not_block_the_delete(self):
        credential = self._make_credential("audit may fail")
        credential_id = credential.id

        log_model = type(self.env["credential.access.log"])
        original = log_model.create

        def exploding_create(self, vals_list):
            raise ValueError("audit backend down")

        log_model.create = exploding_create
        try:
            credential.unlink()
        finally:
            log_model.create = original

        self.assertFalse(
            self.env["credential.credential"].browse(credential_id).exists(),
            "audit integrity is best-effort; it must never block a deletion",
        )


@tagged("post_install", "-at_install")
class TestCredentialUnlinkRealCursor(CredentialUnlinkCommon):
    def test_unlink_on_a_real_cursor(self):
        registry = self.env.registry
        dbname = self.env.cr.dbname
        category_id = self.category.id
        name = "real cursor unlink"

        with registry.cursor() as cr:
            env = self.env(cr=cr)
            credential = env["credential.credential"].create(
                {
                    "name": name,
                    "category_id": category_id,
                    "api_key": "SECRET",
                }
            )
            credential_id = credential.id
            cr.commit()

        try:
            with registry.cursor() as cr:
                env = self.env(cr=cr)
                env["credential.credential"].browse(credential_id).unlink()
                cr.commit()

            with registry.cursor() as cr:
                env = self.env(cr=cr)
                self.assertFalse(
                    env["credential.credential"].browse(credential_id).exists(),
                    "the credential must actually be gone",
                )
                rows = (
                    env["credential.access.log"]
                    .sudo()
                    .search(
                        [("operation", "=", "delete"), ("credential_name", "=", name)]
                    )
                )
                self.assertEqual(
                    len(rows),
                    1,
                    "exactly one delete audit row -- a retry loop used to leave "
                    "one per attempt for a deletion that never happened",
                )
        finally:
            with registry.cursor() as cr:
                cr.execute(
                    "DELETE FROM credential_access_log WHERE credential_name = %s",
                    [name],
                )
                cr.execute(
                    "DELETE FROM credential_credential WHERE id = %s",
                    [credential_id],
                )
                cr.commit()
        self.assertEqual(dbname, self.env.cr.dbname)
