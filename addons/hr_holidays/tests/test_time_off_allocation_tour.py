from odoo.tests import HttpCase, tagged, users


@tagged("post_install", "-at_install")
class TestTimeOffAllocationTour(HttpCase):

    @users('admin')
    def test_time_off_allocation_warning_tour(self):
        self.start_tour("/", "time_off_allocation_warning_tour", login="admin")
