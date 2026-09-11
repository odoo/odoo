# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests.common import tagged, TransactionCase


class TestHrAttendanceScenario(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env.company.country_id = cls.env.ref('base.us')

    def test_load_scenario(self):
        self.env['hr.attendance']._load_demo_data()
