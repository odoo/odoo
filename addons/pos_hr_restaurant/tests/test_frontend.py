from odoo.tests import tagged
from odoo.addons.pos_hr.tests.test_frontend import TestPosHrHttpCommon
from odoo.addons.pos_restaurant.tests.test_frontend import TestFrontendCommon


@tagged("post_install", "-at_install")
class TestUi(TestPosHrHttpCommon, TestFrontendCommon):
    def test_post_login_default_screen_tables(self):
        self.main_pos_config.default_screen = "tables"
        self.main_pos_config.with_user(self.pos_admin).open_ui()
        self.start_pos_tour("test_post_login_default_screen_is_tables", login="pos_admin")

    def test_post_login_default_screen_register(self):
        self.main_pos_config.default_screen = "register"
        self.main_pos_config.with_user(self.pos_admin).open_ui()
        self.start_pos_tour("test_post_login_default_screen_is_register", login="pos_admin")
