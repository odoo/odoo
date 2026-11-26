from odoo.tests import tagged
from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.addons.account.tests.taxable_supply_date_common import TestTaxableSupplyDateWithLockDatesMixin


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestTaxableSupplyDateWithLockDates(TestTaxableSupplyDateWithLockDatesMixin, AccountTestInvoicingCommon):
    _test_user_groups = None  # FIXME list needed groups
    other_currency_code = 'EUR'

    @classmethod
    @AccountTestInvoicingCommon.setup_country('pl')
    def setUpClass(cls):
        super().setUpClass()
