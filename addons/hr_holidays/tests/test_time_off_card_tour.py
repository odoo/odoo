from odoo.tests import HttpCase, tagged, users

@tagged('post_install', '-at_install')
class TestTimeOffCardTour(HttpCase):

    @users('admin')
    def test_time_off_card_tour(self):
        self.start_tour('/', 'time_off_card_tour', login='admin')
