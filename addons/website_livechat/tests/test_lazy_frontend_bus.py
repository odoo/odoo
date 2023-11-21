# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.website_livechat.tests.common import TestLivechatCommon
from odoo.tests import HttpCase, tagged


@tagged("post_install", "-at_install")
class TestBusLazyFrontendBus(HttpCase, TestLivechatCommon):
    def test_bus_not_started(self):
        self.start_tour("/", "website_livechat.lazy_frontend_bus")
