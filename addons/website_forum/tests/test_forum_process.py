# Part of Odoo. See LICENSE file for full copyright and licensing details.

import odoo.tests


@odoo.tests.common.at_install(False)
@odoo.tests.common.post_install(True)
class TestUi(odoo.tests.HttpCase):
    def test_01_admin_forum_tour(self):
        self.phantom_js("/", "odoo.__DEBUG__.services['web_tour.tour'].run('question')", "odoo.__DEBUG__.services['web_tour.tour'].tours.question", login="admin")

    def test_02_demo_question(self):
        self.phantom_js("/", "odoo.__DEBUG__.services['web.Tour'].run('forum_question', 'test')", "odoo.__DEBUG__.services['web.Tour'].tours.forum_question", login="demo")
