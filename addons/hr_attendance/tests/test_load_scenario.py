# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests.common import TransactionCase


class TestHrAttendance(TransactionCase):
    def test_load_scenario(self):
        self.env['hr_attendance']._load_demo_data()
