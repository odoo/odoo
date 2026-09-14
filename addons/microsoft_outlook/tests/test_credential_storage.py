"""The Outlook tokens rest in the vault; the fields are doors, not stores."""

from odoo.tests import TransactionCase, tagged


ACCESS = "microsoft_outlook_access_token"
REFRESH = "microsoft_outlook_refresh_token"


@tagged("post_install", "-at_install")
class TestOutlookCredentials(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.server = cls.env["ir.mail_server"].create(
            {
                "name": "Outlook Server",
                "smtp_host": "smtp.example.com",
            }
        )

    def _set(self, **tokens):
        self.server.write(tokens)
        self.server.invalidate_recordset()

    def test_writing_tokens_creates_one_credential_holding_both(self):
        self._set(**{ACCESS: "an-access", REFRESH: "a-refresh"})

        credential = self.server.oauth2_credential_id.sudo()
        self.assertTrue(credential)
        self.assertEqual(credential.oauth_access_token, "an-access")
        self.assertEqual(credential.oauth_refresh_token, "a-refresh")

    def test_the_fields_read_back_what_was_written(self):
        self._set(**{ACCESS: "round-access", REFRESH: "round-refresh"})

        self.assertEqual(self.server[ACCESS], "round-access")
        self.assertEqual(self.server[REFRESH], "round-refresh")

    def test_renewing_the_access_token_leaves_the_refresh_token_alone(self):
        # This is what `_renew_..._access_token` does: it writes the access token
        # and nothing else. A store that could not tell "not given" from "given
        # as empty" would discard the refresh token every time it was used.
        self._set(**{ACCESS: "first", REFRESH: "the-refresh"})

        self._set(**{ACCESS: "second"})

        self.assertEqual(self.server[ACCESS], "second")
        self.assertEqual(
            self.server[REFRESH],
            "the-refresh",
            "a renewal must not discard the token it renewed with",
        )

    def test_clearing_both_unlinks_the_credential(self):
        self._set(**{ACCESS: "gone", REFRESH: "gone-refresh"})
        credential = self.server.oauth2_credential_id

        self._set(**{ACCESS: False, REFRESH: False})

        self.assertFalse(self.server.oauth2_credential_id)
        self.assertFalse(credential.exists())

    def test_a_server_with_no_tokens_reads_empty(self):
        self.assertFalse(self.server.oauth2_credential_id)
        self.assertFalse(self.server[ACCESS])
        self.assertFalse(self.server[REFRESH])

    def test_no_plaintext_column_survives(self):
        self.env.cr.execute(
            """
            SELECT table_name, column_name FROM information_schema.columns
             WHERE table_name IN ('ir_mail_server', 'fetchmail_server')
               AND column_name IN (%s, %s)
            """,
            (ACCESS, REFRESH),
        )
        self.assertEqual(
            self.env.cr.fetchall(),
            [],
            "the migration drops the columns on BOTH tables the mixin reaches; "
            "a nulled column still sits in every backup taken before it was nulled",
        )

    def test_the_expiry_is_not_a_secret_and_stays_a_column(self):
        field = self.env["ir.mail_server"]._fields[
            "microsoft_outlook_access_token_expiration"
        ]
        self.assertTrue(field.store)
