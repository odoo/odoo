import tempfile
import textwrap
import unittest
from pathlib import Path

from odoo.tools.config import configmanager


class TestInlineComments(unittest.TestCase):
    def _load(self, body: str) -> dict:
        with tempfile.TemporaryDirectory() as tmp:
            rcfile = Path(tmp) / "odoo.conf"
            rcfile.write_text(textwrap.dedent(body).lstrip())
            config = configmanager()
            config._load_file_options(str(rcfile))
            return dict(config._file_options)

    def test_semicolon_comment_is_stripped_from_a_string_option(self):
        options = self._load("""
            [options]
            db_host = /var/run/postgresql ; the socket directory
        """)
        self.assertEqual(options["db_host"], "/var/run/postgresql")

    def test_hash_comment_is_stripped_from_a_string_option(self):
        options = self._load("""
            [options]
            db_host = /var/run/postgresql # the socket directory
        """)
        self.assertEqual(options["db_host"], "/var/run/postgresql")

    def test_trailing_comment_no_longer_breaks_a_typed_option(self):
        options = self._load("""
            [options]
            db_port = 5432 ; the default
        """)
        self.assertEqual(options["db_port"], 5432)

    def test_prefix_without_leading_whitespace_stays_part_of_the_value(self):
        options = self._load("""
            [options]
            db_host = left;right#middle
        """)
        self.assertEqual(options["db_host"], "left;right#middle")

    def test_whole_line_comments_still_work(self):
        options = self._load("""
            [options]
            ; a semicolon line
            # a hash line
            db_host = localhost
        """)
        self.assertEqual(options["db_host"], "localhost")

    def test_comment_only_value_reads_as_empty(self):
        options = self._load("""
            [options]
            db_host = ; unset, use the unix socket
        """)
        self.assertEqual(options["db_host"], "")


class TestEmptyValueIsUnset(TestInlineComments):
    def test_an_empty_boolean_or_integer_is_left_to_its_default(self):
        options = self._load("""
            [options]
            db_discard_on_return =
            db_port =
            db_host =
        """)
        self.assertNotIn("db_discard_on_return", options)
        self.assertNotIn("db_port", options)
        self.assertEqual(options["db_host"], "")


if __name__ == "__main__":
    unittest.main()
