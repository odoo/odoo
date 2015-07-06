import pytest
import openerp.tests

@openerp.tests.common.at_install(False)
@openerp.tests.common.post_install(True)
class TestUi(openerp.tests.HttpCase):
    @pytest.mark.skipif(reason="Not previously imported -> not working and not run")
    def test_01_admin_forum_tour(self):
        self.phantom_js("/", "odoo.__DEBUG__.services['web.Tour'].run('question', 'test')", "odoo.__DEBUG__.services['web.Tour'].tours.question", login="admin")

    @pytest.mark.skipif(reason="Not previously imported -> not working and not run")
    def test_02_demo_question(self):
        self.phantom_js("/", "odoo.__DEBUG__.services['web.Tour'].run('forum_question', 'test')", "odoo.__DEBUG__.services['web.Tour'].tours.forum_question", login="demo")
