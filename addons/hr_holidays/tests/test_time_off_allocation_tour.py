from odoo.tests import HttpCase, tagged
from odoo.addons.hr.tests.test_utils import get_admin_employee


@tagged("post_install", "-at_install")
class TestTimeOffAllocationTour(HttpCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env.company.country_id = cls.env.ref('base.us')

    def test_time_off_allocation_warning_tour(self):
        self.admin_employee = get_admin_employee(self.env)
        self.start_tour("/odoo", "time_off_allocation_warning_tour", login="admin")
