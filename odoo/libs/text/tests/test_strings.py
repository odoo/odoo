import unittest

from odoo.libs.text.strings import get_flag


class TestGetFlag(unittest.TestCase):
    def test_uppercase_code(self):
        self.assertEqual(get_flag("US"), "\U0001f1fa\U0001f1f8")

    def test_lowercase_code_does_not_crash(self):
        self.assertEqual(get_flag("us"), get_flag("US"))
        self.assertEqual(get_flag("mx"), get_flag("MX"))


if __name__ == "__main__":
    unittest.main()


def test_split_refs_skips_the_empty_item_a_trailing_comma_leaves():
    from odoo.libs.text.strings import split_refs

    assert split_refs("") == []
    assert split_refs("base.group_user, ,base.group_system,") == [
        "base.group_user",
        "base.group_system",
    ]
