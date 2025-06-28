# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests.common import TransactionCase

from odoo.addons.mail.tests.common import mail_new_test_user

class TestContractPublicAccess(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.company = cls.env['res.company'].create({'name': 'mami rock'})
        cls.manager_user = mail_new_test_user(
            cls.env,
            name='manager_user',
            login='manager_user',
            email='manager_user@example.com',
            notification_type='email',
            groups='base.group_user',
            company_id=cls.company.id,
        )

        cls.manager = cls.env['hr.employee'].create({
            'name': 'Johnny',
            'user_id': cls.manager_user.id,
            'company_id': cls.company.id,
        })

        cls.employee_a, cls.employee_b = cls.env['hr.employee'].create([{
            'name': 'David',
            'parent_id': cls.manager.id,
            'company_id': cls.company.id,
        }, {
            'name': 'Laura',
            'company_id': cls.company.id,
        }])
        cls.employee_c = cls.env['hr.employee'].create({
            'name': 'Jade',
            'parent_id': cls.employee_a.id,
            'company_id': cls.company.id,
        })

        cls.contract_a, cls.contract_b, cls.contract_c = cls.env['hr.contract'].create([{
            'name': 'contract johnny',
            'employee_id': cls.employee_a.id,
            'state': 'open',
            'wage': 1,
            'date_start': '2017-12-05',
            'company_id': cls.company.id,
        }, {
            'name': 'contract laura',
            'employee_id': cls.employee_b.id,
            'state': 'open',
            'wage': 1,
            'date_start': '2018-12-05',
            'company_id': cls.company.id,
        }, {
            'name': 'contract jade',
            'employee_id': cls.employee_c.id,
            'state': 'open',
            'wage': 1,
            'date_start': '2019-12-05',
            'company_id': cls.company.id,
        }])

    def test_manager(self):
        with self.with_user(self.manager_user.login):
            david, laura, jade = self.env['hr.employee.public'].browse((self.employee_a | self.employee_b | self.employee_c).ids)

            self.assertTrue(david.is_manager)
            self.assertFalse(laura.is_manager)
            self.assertTrue(jade.is_manager)

    def test_manager_access_read(self):
        with self.with_user(self.manager_user.login):
            david, laura, jade = self.env['hr.employee.public'].browse((self.employee_a | self.employee_b | self.employee_c).ids)

            # Should be able to read direct reports and indirect reports first_contract_date
            self.assertEqual(str(david.first_contract_date), '2017-12-05')
            self.assertEqual(str(jade.first_contract_date), '2019-12-05')

            # Cannot read on an employee the user is not manager of
            self.assertFalse(laura.first_contract_date)

    def test_manager_access_search(self):
        with self.with_user(self.manager_user.login):
            employees = self.env['hr.employee.public'].search([('first_contract_date', '>=', '2017-12-05')])

            # Should not find Laura as the user is not her manager
            self.assertEqual(len(employees), 2)
            self.assertTrue('Laura' not in employees.mapped('name'))
