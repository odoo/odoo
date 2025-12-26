# Copyright 2016-2017 Versada <https://versada.eu/>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
import os

from odoo.tests import TransactionCase

from .. import logutils


class TestOdooCookieSanitizer(TransactionCase):
    def test_cookie_as_string(self):
        data = {
            "request": {
                "cookies": "website_lang=en_us;"
                "session_id=hello;"
                "Session_ID=hello;"
                "foo=bar"
            }
        }

        proc = logutils.SanitizeOdooCookiesProcessor()
        result = proc.process(data)

        self.assertTrue("request" in result)
        http = result["request"]
        self.assertEqual(
            http["cookies"],
            "website_lang=en_us;"
            f"session_id={proc.MASK};"
            f"Session_ID={proc.MASK};"
            "foo=bar",
        )

    def test_cookie_as_string_with_partials(self):
        data = {"request": {"cookies": "website_lang=en_us;session_id;foo=bar"}}

        proc = logutils.SanitizeOdooCookiesProcessor()
        result = proc.process(data)

        self.assertTrue("request" in result)
        http = result["request"]
        self.assertEqual(
            http["cookies"],
            "website_lang=en_us;session_id;foo=bar",
        )

    def test_cookie_header(self):
        data = {
            "request": {
                "headers": {
                    "Cookie": "foo=bar;"
                    "session_id=hello;"
                    "Session_ID=hello;"
                    "a_session_id_here=hello"
                }
            }
        }

        proc = logutils.SanitizeOdooCookiesProcessor()
        result = proc.process(data)

        self.assertTrue("request" in result)
        http = result["request"]
        self.assertEqual(
            http["headers"]["Cookie"],
            "foo=bar;"
            f"session_id={proc.MASK};"
            f"Session_ID={proc.MASK};"
            f"a_session_id_here={proc.MASK}",
        )

    def test_git_sha_failure(self):
        with self.assertRaises(logutils.InvalidGitRepository):
            # Assume this test file is not in the repo root
            logutils.fetch_git_sha(os.path.dirname(__file__))
