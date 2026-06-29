from odoo.tests import tagged
from odoo.addons.pos_hr.tests.test_frontend import TestPosHrHttpCommon
from odoo.addons.pos_restaurant.tests.test_frontend import TestFrontendCommon


@tagged("post_install", "-at_install")
class TestUi(TestPosHrHttpCommon, TestFrontendCommon):
    _test_groups = None  # FIXME list needed groups

    def test_post_login_default_screen_tables(self):
        self.main_pos_config.default_screen = "tables"
        self.main_pos_config.with_user(self.pos_admin).open_ui()
        self.start_pos_tour("test_post_login_default_screen_is_tables", login="pos_admin")

    def test_post_login_default_screen_register(self):
        self.main_pos_config.default_screen = "register"
        self.main_pos_config.with_user(self.pos_admin).open_ui()
        self.start_pos_tour("test_post_login_default_screen_is_register", login="pos_admin")

    def test_employee_chatter_with_tracked_order(self):
        """
        Tests that when changing the session's employee mid session,
        the message in the chatter created with the track order setting
        will reflect this change and not keep the old employee
        """
        self.main_pos_config.order_edit_tracking = True
        self.main_pos_config.open_ui()
        self.start_tour(
            "/pos/ui?config_id=%d" % self.main_pos_config.id,
            "test_employee_chatter_with_tracked_order",
            login="pos_admin",
        )
        order = self.env['pos.order'].search([
            ('config_id', '=', self.main_pos_config.id)
        ], order='id desc', limit=1)
        self.assertNotIn("Mitchell Admin", order.message_ids[0].body)
