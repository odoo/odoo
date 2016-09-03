# Part of Odoo. See LICENSE file for full copyright and licensing details.

import odoo.tests


@odoo.tests.common.at_install(False)
@odoo.tests.common.post_install(True)
class TestUi(odoo.tests.HttpCase):
    def test_admin(self):
        self.phantom_js("/", "odoo.__DEBUG__.services['web_tour.tour'].run('blog')", "odoo.__DEBUG__.services['web_tour.tour'].tours.blog.ready", login='admin')
