# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
import odoo.tests

from requests import Session, PreparedRequest, Response

from datetime import datetime
from odoo.addons.base.tests.common import HttpCaseWithUserDemo
from dateutil.relativedelta import relativedelta

_logger = logging.getLogger(__name__)


@odoo.tests.tagged('click_all', 'post_install', '-at_install', '-standard')
class TestMenusAdmin(odoo.tests.HttpCase):
    allow_end_on_form = True
    def test_01_click_everywhere_as_admin(self):
        menus = self.env['ir.ui.menu'].load_menus(False)
        for app_id in menus['root']['children']:
            with self.subTest(app=menus[app_id]['name']):
                _logger.runbot('Testing %s', menus[app_id]['name'])
                self.browser_js("/odoo", "odoo.loader.modules.get('@web/webclient/clickbot/clickbot_loader').startClickEverywhere('%s');" % menus[app_id]['xmlid'], "odoo.isReady === true", login="admin", timeout=1200, success_signal="clickbot test succeeded")


@odoo.tests.tagged('click_all', 'post_install', '-at_install', '-standard')
class TestMenusDemo(HttpCaseWithUserDemo):
    allow_end_on_form = True
    def test_01_click_everywhere_as_demo(self):
        user_demo = self.env.ref("base.user_demo")
        menus = self.env['ir.ui.menu'].with_user(user_demo.id).load_menus(False)
        for app_id in menus['root']['children']:
            with self.subTest(app=menus[app_id]['name']):
                _logger.runbot('Testing %s', menus[app_id]['name'])
                self.browser_js("/odoo", "odoo.loader.modules.get('@web/webclient/clickbot/clickbot_loader').startClickEverywhere('%s');" % menus[app_id]['xmlid'], "odoo.isReady === true", login="demo", timeout=1200, success_signal="clickbot test succeeded")

@odoo.tests.tagged('post_install', '-at_install')
class TestMenusAdminLight(odoo.tests.HttpCase):
    allow_end_on_form = True

    @classmethod
    def _request_handler(cls, s: Session, r: PreparedRequest, /, **kw):
        # mock odoofin requests
        if 'proxy/v1/get_dashboard_institutions' in r.url:
            r = Response()
            r.status_code = 200
            r.json = lambda: {'result': {}}
            return r
        return super()._request_handler(s, r, **kw)

    def test_01_click_apps_menus_as_admin(self):
        # Due to action_pos_preparation_display_kitchen_display, cliking on the "Kitchen Display"
        # menuitem could open the UI display, which will break the crawler tests as there is no
        # way for the tour to be executed, leading to a timeout
        if 'pos_preparation_display.display' in self.env:
            self.env['pos_preparation_display.display'].create({
                'name': 'Super Smart Kitchen Display',
            })
        # There is a bug when we go the Field Service app (without any demo data) and we
        # click on the Studio button. It seems the fake group generated containing one record
        # to be used in the KanbanEditorRenderer has groupByField to undefined
        # (I guess it is because there is no group by?) and we got an error at this line
        # because we assume groupByField is defined.
        if 'project.task' in self.env and 'is_fsm' in self.env['project.task']:
            self.env['project.task'].create({
                'name': 'Zizizbroken',
                'project_id': self.env.ref('industry_fsm.fsm_project').id,
                'user_ids': [(4, self.env.ref('base.user_admin').id)],
                'date_deadline': datetime.now() + relativedelta(hour=12),
                'planned_date_begin': datetime.now() + relativedelta(hour=10),
            })
        self.browser_js("/odoo", "odoo.loader.modules.get('@web/webclient/clickbot/clickbot_loader').startClickEverywhere(undefined, true);", "odoo.isReady === true", login="admin", timeout=120, success_signal="clickbot test succeeded")

@odoo.tests.tagged('post_install', '-at_install')
class TestMenusDemoLight(HttpCaseWithUserDemo):
    allow_end_on_form = True

    def test_01_click_apps_menus_as_demo(self):
        # If not enabled (like in demo data), landing on website dashboard will redirect to /
        # and make the test crash
        group_website_designer = self.env.ref('website.group_website_designer', raise_if_not_found=False)
        if group_website_designer:
            self.env.ref('base.group_user').write({"implied_ids": [(4, group_website_designer.id)]})
        self.browser_js("/odoo", "odoo.loader.modules.get('@web/webclient/clickbot/clickbot_loader').startClickEverywhere(undefined, true);", "odoo.isReady === true", login="demo", timeout=120, success_signal="clickbot test succeeded")
