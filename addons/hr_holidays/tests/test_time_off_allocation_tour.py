from odoo.tests import HttpCase, tagged
from odoo.addons.hr.tests.test_utils import get_admin_employee
from odoo.addons.mail.tests.common import mail_new_test_user


@tagged("post_install", "-at_install")
class TestTimeOffAllocationTour(HttpCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env.company.country_id = cls.env.ref('base.us')

    def test_time_off_allocation_warning_tour(self):
        self.admin_employee = get_admin_employee(self.env)
        self.start_tour("/odoo", "time_off_allocation_warning_tour", login="admin")

    def test_employee_allocation_request_entry_points_visibility(self):
        employee_user = mail_new_test_user(
            self.env,
            login='alloc_visibility_emp',
            groups='hr_holidays.group_hr_holidays_employee',
        )
        employee = self.env['hr.employee'].create({
            'name': 'Allocation Visibility Employee',
            'user_id': employee_user.id,
            'company_id': self.env.company.id,
        })
        WorkEntryType = self.env['hr.work.entry.type']
        WorkEntryType.search([
            ('country_id', '=', self.env.company.country_id.id),
            ('employee_requests', '=', True),
        ]).employee_requests = False

        # A requestable type in another country must not enable entry points
        WorkEntryType.create({
            'name': 'Foreign Requestable Type',
            'code': 'FOREIGN_REQ',
            'count_as': 'absence',
            'country_id': self.env.ref('base.be').id,
            'requires_allocation': True,
            'time_off_selectable': True,
            'employee_requests': True,
        })
        us_type = WorkEntryType.create({
            'name': 'US Non-Requestable Allocation',
            'code': 'US_NO_REQ',
            'count_as': 'absence',
            'country_id': self.env.company.country_id.id,
            'requires_allocation': True,
            'time_off_selectable': True,
            'employee_requests': False,
            'allocation_validation_type': 'no_validation',
            'request_unit': 'day',
            'unit_of_measure': 'day',
        })
        self.env['hr.leave.allocation'].create({
            'employee_id': employee.id,
            'work_entry_type_id': us_type.id,
            'number_of_days': 5,
        })

        self.start_tour("/odoo", "time_off_allocation_request_hidden_tour", login=employee_user.login)

        us_type.employee_requests = True
        self.start_tour("/odoo", "time_off_allocation_request_visible_tour", login=employee_user.login)
