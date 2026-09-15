import unittest

from odoo.libs.password import (
    CryptContext,
    _ab64_decode,
    _ab64_encode,
    _parse_hash,
    pbkdf2_sha512_hash,
)

MALFORMED = "$pbkdf2-sha512$1$a$b"
NON_BASE64 = "$pbkdf2-sha512$1$!!!!$!!!!"


class TestMalformedHash(unittest.TestCase):
    def setUp(self):
        self.ctx = CryptContext(schemes=["pbkdf2_sha512", "plaintext"])

    def test_parse_hash_returns_none_instead_of_raising(self):
        self.assertIsNone(_parse_hash(MALFORMED))
        self.assertIsNone(_parse_hash("not a hash at all"))
        self.assertIsNone(_parse_hash(""))

    def test_parse_hash_tolerates_lenient_base64(self):
        self.assertEqual(_parse_hash(NON_BASE64), (1, b"", b""))

    def test_verify_answers_false_for_a_malformed_hash(self):
        for bad in (MALFORMED, NON_BASE64):
            with self.subTest(hash=bad):
                self.assertFalse(self.ctx.is_password_valid("whatever", bad))

    def test_verify_and_update_answers_false_for_a_malformed_hash(self):
        for bad in (MALFORMED, NON_BASE64):
            with self.subTest(hash=bad):
                self.assertEqual(
                    self.ctx.match_and_update("whatever", bad), (False, None)
                )

    def test_a_malformed_hash_does_not_fall_through_to_plaintext(self):
        self.assertFalse(self.ctx.is_password_valid(MALFORMED, MALFORMED))
        self.assertFalse(self.ctx.is_password_valid(NON_BASE64, NON_BASE64))

    def test_plaintext_fallback_still_applies_to_non_mcf_values(self):
        self.assertTrue(self.ctx.is_password_valid("legacy-plain", "legacy-plain"))

    def test_real_hashes_still_verify(self):
        hashed = pbkdf2_sha512_hash("s3cret", rounds=1000)
        self.assertTrue(self.ctx.is_password_valid("s3cret", hashed))
        self.assertFalse(self.ctx.is_password_valid("s3cre", hashed))

    def test_plaintext_scheme_is_unaffected(self):
        self.assertTrue(self.ctx.is_password_valid("hunter2", "hunter2"))
        self.assertFalse(self.ctx.is_password_valid("hunter2", "hunter3"))


class TestAdaptedBase64Padding(unittest.TestCase):
    def test_round_trip_for_every_length_class(self):
        for size in range(33):
            raw = bytes(range(size))
            with self.subTest(size=size, mod=len(_ab64_encode(raw)) % 4):
                self.assertEqual(_ab64_decode(_ab64_encode(raw)), raw)

    def test_no_surplus_padding_on_aligned_input(self):
        encoded = _ab64_encode(b"abc")
        self.assertEqual(len(encoded) % 4, 0)
        self.assertEqual(_ab64_decode(encoded), b"abc")


if __name__ == "__main__":
    unittest.main()
