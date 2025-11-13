# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests.common import tagged, TransactionCase


@tagged('at_install', '-post_install')  # LEGACY at_install
class TestHrScenario(TransactionCase):

    def test_load_scenario(self):
        self.env['hr.employee']._load_scenario()
