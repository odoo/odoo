import odoo.tests


@odoo.tests.common.tagged('post_install', '-at_install')
class TestUi(odoo.tests.HttpCase):

    def test_01_admin_widget_x2many(self):
        self.phantom_js("/web#action=test_new_api.action_discussions",
                        "odoo.__DEBUG__.services['web_tour.tour'].run('widget_x2many', 100)",
                        "odoo.__DEBUG__.services['web_tour.tour'].tours.widget_x2many.ready",
                        login="admin", timeout=120)
