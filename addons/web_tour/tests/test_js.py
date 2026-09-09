import odoo.tests
from odoo.addons.web.tests.test_js import HootCommon, unit_test_error_checker


@odoo.tests.tagged('post_install', '-at_install')
class WebTourHootSuite(HootCommon):
    @odoo.tests.no_retry
    def test_unit_desktop(self):
        addons_from_asset_bundle = self._get_addons_from_asset_bundle('web.assets_unit_tests')
        filters = self._get_hoot_filters(addons_from_asset_bundle, ['web_tour'])
        if not filters:
            self.fail("web_tour hoot tests not found in the unit tests asset bundle")
        self.browser_js(
            f'/web/tests?&headless&loglevel=2&preset=desktop&timeout=15000{filters}',
            "", "", login='admin', timeout=1800,
            success_signal="[HOOT] Test suite succeeded",
            error_checker=unit_test_error_checker,
        )
