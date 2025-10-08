from odoo.tests import HttpCase, tagged
from odoo.addons.hr.tests.test_utils import get_admin_employee


@tagged("post_install", "-at_install")
class TestTimeOffAllocationTour(HttpCase):

    def test_time_off_allocation_warning_tour(self):
        self.admin_employee = get_admin_employee(self.env)
        self.start_tour("/", "time_off_allocation_warning_tour", login="admin")
