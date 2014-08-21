import openerp.tests

@openerp.tests.common.at_install(False)
@openerp.tests.common.post_install(True)
class TestUi(openerp.tests.HttpCase):
    def test_01_admin_forum_tour(self):
        self.phantom_js("/", "openerp.Tour.run('question', 'test')", "openerp.Tour.tours.question", login="admin")

    def test_02_demo_question(self):
        self.phantom_js("/", "openerp.Tour.run('forum_question', 'test')", "openerp.Tour.tours.forum_question", login="demo")

