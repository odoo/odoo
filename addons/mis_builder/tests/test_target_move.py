# Copyright 2016 ACSONE SA/NV (<http://acsone.eu>)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

import odoo.tests.common as common


class TestMisReportInstance(common.TransactionCase):
    def test_supports_target_move_filter(self):
        self.assertTrue(
            self.env["mis.report"]._supports_target_move_filter("account.move.line")
        )

    def test_supports_target_move_filter_no_parent_state(self):
        self.assertFalse(
            self.env["mis.report"]._supports_target_move_filter("account.move")
        )

    def test_target_move_domain_posted(self):
        self.assertEqual(
            self.env["mis.report"]._get_target_move_domain(
                "posted", "account.move.line"
            ),
            [("parent_state", "=", "posted")],
        )

    def test_target_move_domain_all(self):
        self.assertEqual(
            self.env["mis.report"]._get_target_move_domain("all", "account.move.line"),
            [("parent_state", "in", ("posted", "draft"))],
        )

    def test_target_move_domain_no_parent_state(self):
        """Test get_target_move_domain on a model that has no parent_state."""
        self.assertEqual(
            self.env["mis.report"]._get_target_move_domain("all", "account.move"), []
        )
