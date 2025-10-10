import logging

from odoo import SUPERUSER_ID
from odoo.api import Environment
from odoo.modules.registry import Registry
from odoo.tests import tagged
from odoo.tests.common import get_db_name

from odoo.addons.account.tests.test_l10n import TestL10n
from odoo.addons.account_reports.tests.test_balance_sheet_balanced import (
    TestBalanceSheetBalanced,
)

_logger = logging.getLogger(__name__)


with Registry(get_db_name()).cursor() as cr:
    env = Environment(cr, SUPERUSER_ID, {})
    cr.execute("SELECT id, code FROM res_country ORDER BY code")
    for (country_id, country_code) in cr.fetchall():
        @tagged('-at_install', 'post_install', 'post_install_l10n', 'test_country')
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
