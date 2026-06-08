import odoo.tests

from odoo.addons.base.tests.common import HttpCaseWithUserDemo


@odoo.tests.common.tagged('post_install', '-at_install')
class TestX2Many(HttpCaseWithUserDemo):

    def test_01_admin_widget_x2many(self):
        # /!\This test depends on `web_tour` but since `web_tour` is auto installed
        # and this test is `post_install`, we don't want to wait for `web_tour` to install
        # before running all the tests at_install in this module. That is why that dependency
        # is not clearly written in the manifest.

        # FIXME: breaks if too many children of base.menu_tests

        # This tour turns out to be quite sensible to the number of items in
        # the base.menu_tests: it's specifically sequenced to be lower (after)
        # the default, but doesn't account for the fact that it could
        # "fall off" into the "o_extra_menu_items" section if the window is
        # too small or there are too many items preceding it in the tests menu
        self.start_tour("/odoo/action-test_orm.action_discussions",
            'widget_x2many', login="admin", timeout=120)
