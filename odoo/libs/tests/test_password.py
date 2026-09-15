import unittest

from odoo.libs.password import _MAX_ROUNDS, CryptContext, pbkdf2_sha512_hash


class TestCryptContextRoundTrip(unittest.TestCase):
    def test_hash_and_verify_round_trip(self):
        ctx = CryptContext()
        hashed = ctx.hash("s3cret")
        self.assertTrue(ctx.is_password_valid("s3cret", hashed))
        self.assertFalse(ctx.is_password_valid("wrong", hashed))

    def test_schemes_and_copy(self):
        ctx = CryptContext(schemes=["pbkdf2_sha512", "plaintext"])
        self.assertEqual(ctx.schemes(), ["pbkdf2_sha512", "plaintext"])
        clone = ctx.copy()
        self.assertEqual(clone.schemes(), ctx.schemes())
        self.assertTrue(clone.is_password_valid("hunter2", "hunter2"))

    def test_update_changes_schemes_deprecated_and_rounds(self):
        ctx = CryptContext()
        ctx.update(
            schemes=["pbkdf2_sha512", "plaintext"],
            deprecated=["plaintext"],
            pbkdf2_sha512__rounds=1000,
        )
        self.assertEqual(ctx.schemes(), ["pbkdf2_sha512", "plaintext"])
        hashed = pbkdf2_sha512_hash("s3cret", rounds=500)
        ok, replacement = ctx.match_and_update("s3cret", hashed)
        self.assertTrue(ok)
        self.assertIsNotNone(replacement)

    def test_match_and_update_flags_deprecated_scheme(self):
        ctx = CryptContext(
            schemes=["pbkdf2_sha512", "plaintext"], deprecated=["plaintext"]
        )
        ok, replacement = ctx.match_and_update("hunter2", "hunter2")
        self.assertTrue(ok)
        self.assertIsNotNone(replacement)


class TestCryptContextSchemesStringGuard(unittest.TestCase):
    def test_init_accepts_a_bare_scheme_string(self):
        ctx = CryptContext("pbkdf2_sha512")  # type: ignore[arg-type]  # a bare string is the case under test
        self.assertEqual(ctx.schemes(), ["pbkdf2_sha512"])


class TestCryptContextVerifyRespectsSchemes(unittest.TestCase):
    def test_a_well_formed_hash_is_rejected_when_the_scheme_is_disabled(self):
        ctx = CryptContext(schemes=["plaintext"])
        hashed = pbkdf2_sha512_hash("s3cret")
        self.assertFalse(ctx.is_password_valid("s3cret", hashed))


class TestCryptContextRoundsBoundEnforcement(unittest.TestCase):
    def test_init_rejects_rounds_above_the_max(self):
        with self.assertRaises(ValueError):
            CryptContext(pbkdf2_sha512__rounds=_MAX_ROUNDS + 1000)

    def test_init_rejects_zero_rounds(self):
        with self.assertRaises(ValueError):
            CryptContext(pbkdf2_sha512__rounds=0)

    def test_update_rejects_rounds_above_the_max(self):
        ctx = CryptContext()
        with self.assertRaises(ValueError):
            ctx.update(pbkdf2_sha512__rounds=_MAX_ROUNDS + 1000)


if __name__ == "__main__":
    unittest.main()
