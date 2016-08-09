import openerp.tests


class TestUi(openerp.tests.HttpCase):

    post_install = True
    at_install = False

    def test_01_admin_forum_tour(self):
        self.phantom_js("/", "odoo.__DEBUG__.services['web_tour.tour'].run('question')", "odoo.__DEBUG__.services['web_tour.tour'].tours.question", login="admin")

    def test_02_demo_question(self):
        self.phantom_js("/", "odoo.__DEBUG__.services['web_tour.tour'].run('forum_question')", "odoo.__DEBUG__.services['web_tour.tour'].tours.forum_question", login="demo")
