import openerp.tests

@openerp.tests.common.at_install(False)
@openerp.tests.common.post_install(True)
class TestUi(openerp.tests.HttpCase):
    def test_01_admin_widget_x2many(self):
        self.phantom_js("/web#action=test_new_api.action_discussions",
                        "odoo.__DEBUG__.services['web.Tour'].run('widget_x2many', 'test')",
                        "odoo.__DEBUG__.services['web.Tour'].tours.widget_x2many",
                        login="admin")
