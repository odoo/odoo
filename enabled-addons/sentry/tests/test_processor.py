from odoo.tests import TransactionCase

from .. import processor


class TestSanitizers(TransactionCase):
    def test_sanitize_password(self):
        sanitizer = processor.SanitizePasswordsProcessor()
        for password in [
            "1234-5678-9012-3456",
            "1234 5678 9012 3456",
            "1234 - 5678- -0987---1234",
            "123456789012345",
        ]:
            with self.subTest(
                password=password,
                msg="password should have been sanitized",
            ):
                self.assertEqual(
                    sanitizer.sanitize(None, password),
                    sanitizer.MASK,
                )
        for not_password in [
            "1234",
            "hello",
            "text long enough",
            "numbers and 73X7",
            "12345678901234567890",
            b"12345678901234567890",
            b"1234 5678 9012 3456",
            "1234-5678-9012-3456-7890",
        ]:
            with self.subTest(
                not_password=password,
                msg="not_password should not have been sanitized",
            ):
                self.assertEqual(
                    sanitizer.sanitize(None, not_password),
                    not_password,
                )

    def test_sanitize_keys(self):
        sanitizer = processor.SanitizeKeysProcessor()
        self.assertIsNone(sanitizer.sanitize_keys)

    def test_sanitize_none(self):
        sanitizer = processor.SanitizePasswordsProcessor()
        self.assertIsNone(sanitizer.sanitize(None, None))
