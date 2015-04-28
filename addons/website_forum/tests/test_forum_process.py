import openerp.tests

@openerp.tests.category('website')
@openerp.tests.at_install(False)
@openerp.tests.post_install(True)
class TestUi(openerp.tests.HttpCase):
    def test_01_admin_forum_tour(self):
        self.phantom_js("/", "odoo.__DEBUG__.services['web.Tour'].run('question', 'test')", "odoo.__DEBUG__.services['web.Tour'].tours.question", login="admin")

    def test_02_demo_question(self):
        self.phantom_js("/", "odoo.__DEBUG__.services['web.Tour'].run('forum_question', 'test')", "odoo.__DEBUG__.services['web.Tour'].tours.forum_question", login="demo")

