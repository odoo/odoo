# Part of Odoo. See LICENSE file for full copyright and licensing details.

import odoo.tests


@odoo.tests.tagged('click_all', 'post_install', '-at_install', '-standard')
class TestMenusAdmin(odoo.tests.HttpCase):

    def test_01_click_everywhere_as_admin(self):
        self.browser_js("/web", "odoo.__DEBUG__.services['web.clickEverywhere']();", "odoo.isReady === true", login="admin", timeout=45*60)


@odoo.tests.tagged('click_all', 'post_install', '-at_install', '-standard')
class TestMenusDemo(odoo.tests.HttpCase):

    def test_01_click_everywhere_as_demo(self):
        self.browser_js("/web", "odoo.__DEBUG__.services['web.clickEverywhere']();", "odoo.isReady === true", login="demo", timeout=1800)
