from odoo.tests import TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestMySubscription(TransactionCase):

    def test_show_database_action(self):
        icp_sudo = self.env['ir.config_parameter'].sudo()
        my_sub = self.env['mysubscription.mysubscription']

        self.assertTrue(my_sub.get_dashboard_data()['show_database_action'])

        icp_sudo.set_bool('mysubscription.database', False)
        self.assertFalse(my_sub.get_dashboard_data()['show_database_action'])

        icp_sudo.set_bool('mysubscription.database', None)
        self.assertTrue(my_sub.get_dashboard_data()['show_database_action'])
