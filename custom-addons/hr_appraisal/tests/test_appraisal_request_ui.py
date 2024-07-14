from odoo.tests import tagged, HttpCase
from odoo.tests.common import new_test_user


@tagged('post_install', '-at_install')
class TestHrAppraisalRequestUi(HttpCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.manager_user = new_test_user(cls.env, login='Lucky Luke', name='Manager Tiranique')
        cls.manager = cls.env['hr.employee'].create({
            'name': 'Manager Tiranique',
            'user_id': cls.manager_user.id,
        })
        cls.employee_user = new_test_user(cls.env, login='Rantanplan', name='Michael Hawkins')
        cls.employee = cls.env['hr.employee'].create({
            'name': "Michael Hawkins",
            'parent_id': cls.manager.id,
            'work_email': 'michael@odoo.com',
            'user_id': cls.employee_user.id,
        })
        cls.employee.work_email = 'chouxblanc@donc.com'

    def test_send_appraisal_request_by_email_flow(self):
        self.env['hr.appraisal'].search([]).write({'active': False})
        self.env['hr.appraisal'].create({'employee_id': self.employee.id, 'manager_ids': self.employee.parent_id})
        self.start_tour('/web', 'test_send_appraisal_request_by_email_flow', login=self.manager_user.login)
