import logging

from odoo.modules.registry import Registry
from odoo.tests import tagged, BaseCase
from odoo.tests.common import get_db_name

_logger = logging.getLogger(__name__)


class TestL10n(BaseCase):  # fallback if module is not installed
    def _test_domestic_fiscal_position(self):
        self.skipTest('`account` is not installed')

    def _test_load_demo(self):
        self.skipTest('`account` is not installed')


class TestBalanceSheetBalanced(BaseCase):  # fallback if module is not installed
    def _test_report(self):
        self.skipTest('`account_reports` is not installed')


with Registry(get_db_name()).cursor() as cr:
    cr.execute("SELECT name FROM ir_module_module WHERE state = 'installed'")
    installed_modules = {module_name for (module_name,) in cr.fetchall()}
    if 'account' in installed_modules:
        from odoo.addons.account.tests.test_l10n import TestL10n
    if 'account_reports' in installed_modules:
        from odoo.addons.account_reports.tests.test_balance_sheet_balanced import TestBalanceSheetBalanced

    cr.execute("SELECT id, code FROM res_country ORDER BY code")
    for (country_id, country_code) in cr.fetchall():
        @tagged('-at_install', 'post_install', 'post_install_l10n')
        class TestCountry(TestL10n, TestBalanceSheetBalanced):
            def test_report(self):
                self._test_report()

            def test_domestic_fiscal_position(self):
                self._test_domestic_fiscal_position()

            def test_load_demo(self):
                self._test_load_demo()

        TestCountry.country_id = country_id
        TestCountry.country_code = country_code
        class_name = 'Test_' + country_code
        TestCountry.__name__ = TestCountry.__qualname__ = class_name
        globals()[class_name] = TestCountry
