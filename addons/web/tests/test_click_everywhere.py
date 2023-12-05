# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
import odoo.tests
from odoo.addons.base.tests.common import HttpCaseWithUserDemo

_logger = logging.getLogger(__name__)


@odoo.tests.tagged('click_all', 'post_install', '-at_install', '-standard')
class TestMenusAdmin(odoo.tests.HttpCase):
    allow_end_on_form = True
    def test_01_click_everywhere_as_admin(self):
        menus = self.env['ir.ui.menu'].load_menus(False)
        for app_id in menus['root']['children']:
            with self.subTest(app=menus[app_id]['name']):
                _logger.runbot('Testing %s', menus[app_id]['name'])
                self.browser_js("/web", "odoo.loader.modules.get('@web/webclient/clickbot/clickbot_loader').startClickEverywhere('%s');" % menus[app_id]['xmlid'], "odoo.isReady === true", login="admin", timeout=1200)


@odoo.tests.tagged('click_all', 'post_install', '-at_install', '-standard')
class TestMenusDemo(odoo.tests.HttpCase):
    allow_end_on_form = True
    def test_01_click_everywhere_as_demo(self):
        user_demo = self.env.ref("base.user_demo")
        menus = self.env['ir.ui.menu'].with_user(user_demo.id).load_menus(False)
        for app_id in menus['root']['children']:
            with self.subTest(app=menus[app_id]['name']):
                _logger.runbot('Testing %s', menus[app_id]['name'])
                self.browser_js("/web", "odoo.loader.modules.get('@web/webclient/clickbot/clickbot_loader').startClickEverywhere('%s');" % menus[app_id]['xmlid'], "odoo.isReady === true", login="demo", timeout=1200)

@odoo.tests.tagged('post_install', '-at_install')
class TestMenusAdminLight(odoo.tests.HttpCase):
    allow_end_on_form = True
    def test_01_click_apps_menus_as_admin(self):
        # Due to action_pos_preparation_display_kitchen_display, cliking on the "Kitchen Display"
        # menuitem could open the UI display, which will break the crawler tests as there is no
        # way for the tour to be executed, leading to a timeout
        if 'pos_preparation_display.display' in self.env:
            self.env['pos_preparation_display.display'].create({
                'name': 'Super Smart Kitchen Display',
            })
        self.browser_js("/web", "odoo.loader.modules.get('@web/webclient/clickbot/clickbot_loader').startClickEverywhere(undefined, true);", "odoo.isReady === true", login="admin", timeout=120)

@odoo.tests.tagged('post_install', '-at_install')
class TestMenusDemoLight(odoo.tests.HttpCase):
    allow_end_on_form = True

    def test_01_click_apps_menus_as_demo(self):
        # If not enabled (like in demo data), landing on website dashboard will redirect to /
        # and make the test crash
        group_website_designer = self.env.ref('website.group_website_designer', raise_if_not_found=False)
        if group_website_designer:
            self.env.ref('base.group_user').write({"implied_ids": [(4, group_website_designer.id)]})
        self.browser_js("/web", "odoo.loader.modules.get('@web/webclient/clickbot/clickbot_loader').startClickEverywhere(undefined, true);", "odoo.isReady === true", login="demo", timeout=120)
