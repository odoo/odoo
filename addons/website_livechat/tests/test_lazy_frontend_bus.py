# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import tests
from odoo.addons.website_livechat.tests.common import TestWebsiteLivechatCommon


class TestBusLazyFrontendBus(TestWebsiteLivechatCommon, tests.HttpCase):
    def test_bus_not_started(self):
        self.start_tour("/", "website_livechat.lazy_frontend_bus")
