# Copyright 2022 Camptocamp SA (https://www.camptocamp.com).
# @author Iván Todorovich <ivan.todorovich@camptocamp.com>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo.tests import HttpCase, tagged


@tagged("-at_install", "post_install")
class TestQunit(HttpCase):
    def test_qunit(self):
        self.browser_js(
            "/web/tests?module=web_domain_field&failfast",
            "",
            "",
            login="admin",
        )
