# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests.common import TransactionCase


class TestHrBe(TransactionCase):
    def test_employee_insz_number(self):
        employee_before_2000 = self.env['hr.employee'].create({'name': 'Colleague Test', 'birthday': '1997-05-10'})
        employee_before_2000.insz_or_bis_number = '97051000125'

        employee_after_2000 = self.env['hr.employee'].create({'name': 'Colleague Test', 'birthday': '2007-05-10'})
        employee_after_2000.insz_or_bis_number = '07051000107'
