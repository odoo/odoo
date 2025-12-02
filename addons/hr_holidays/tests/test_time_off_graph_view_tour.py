from odoo.tests import HttpCase, tagged, users

@tagged('post_install', '-at_install')
class TestTimeOffGraphViewTour(HttpCase):

    @users('admin')
    def test_time_off_graph_view_tour(self):
        self.start_tour('/', 'time_off_graph_view_tour', login='admin')
