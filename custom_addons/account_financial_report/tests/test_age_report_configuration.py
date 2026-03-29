#  Copyright 2023 Tecnativa - Carolina Fernandez
#  License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo.exceptions import ValidationError
from odoo.tests import common, tagged


@tagged("post_install", "-at_install")
class TestAccountAgeReportConfiguration(common.TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.account_age_report_config = cls.env[
            "account.age.report.configuration"
        ].create(
            {
                "name": "Intervals configuration",
                "line_ids": [
                    (
                        0,
                        0,
                        {
                            "name": "1-30",
                            "inferior_limit": 30,
                        },
                    ),
                ],
            }
        )

    def test_check_line_ids_constraint(self):
        with self.assertRaises(ValidationError):
            self.env["account.age.report.configuration"].create(
                {"name": "Interval configuration", "line_ids": False}
            )

    def test_check_lower_inferior_limit_constraint(self):
        with self.assertRaises(ValidationError):
            self.account_age_report_config.line_ids.inferior_limit = 0

        with self.assertRaises(ValidationError):
            self.account_age_report_config.line_ids.inferior_limit = -1
