# Copyright 2023 Taras Shabaranskyi
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html).

import json
import re

from odoo.tests import HttpCase, tagged


@tagged("-at_install", "post_install")
class TestIrHttp(HttpCase):
    def _test_session_info(self, session_info):
        apps_menu = session_info.get("apps_menu")
        self.assertIsNotNone(apps_menu)
        self.assertTrue("search_type" in apps_menu)
        self.assertTrue("theme" in apps_menu)

    def _find_session_info(self, line_items):
        key = "odoo.__session_info__ = "
        line = next(filter(lambda item: key in item, line_items), None)
        self.assertIsNotNone(line)
        match = re.match(rf".*{key}(.*);", line)
        self.assertIsNotNone(match)
        return match.group(1)

    def test_session_info(self):
        self.authenticate("admin", "admin")
        r = self.url_open("/web")
        self.assertEqual(r.status_code, 200)
        self.assertIsInstance(r.text, str)
        line_items = r.text.splitlines()
        self.assertTrue(bool(line_items))
        session_info_str = self._find_session_info(line_items)
        self.assertIsInstance(session_info_str, str)
        self._test_session_info(json.loads(session_info_str))
