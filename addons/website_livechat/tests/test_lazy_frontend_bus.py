from odoo import tests
from odoo.addons.website_livechat.tests.common import TestLivechatCommon


@tests.tagged("-at_install", "post_install")
class TestBusLazyFrontendBus(tests.HttpCase, TestLivechatCommon):
    def test_bus_not_started(self):
        self.start_tour("/", "website_livechat.lazy_frontend_bus")
