from odoo.tests import HttpCase, tagged, users

@tagged('post_install', '-at_install')
class TestTimeOffCardTour(HttpCase):

    @users('admin')
    def test_time_off_card_tour(self):
        leave_type = self.env['hr.leave.type'].create({
            'name': 'Time Off with no validation for approval',
            'time_type': 'leave',
            'requires_allocation': True,
            'allocation_validation_type': 'no_validation',
        })
        self.env['hr.leave.allocation'].create({
            'employee_id': self.env.user.employee_id.id,
            'holiday_status_id': leave_type.id,
            'allocation_type': 'regular',
            'type_request_unit': 'half_day',
        })
        self.start_tour('/', 'time_off_card_tour', login='admin')
