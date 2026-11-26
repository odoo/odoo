from odoo.tests import tagged
from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.addons.account.tests.taxable_supply_date_common import TestTaxableSupplyDateWithLockDatesMixin


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestTaxableSupplyDateWithLockDates(TestTaxableSupplyDateWithLockDatesMixin, AccountTestInvoicingCommon):
    other_currency_code = 'USD'

    @classmethod
    @AccountTestInvoicingCommon.setup_country('sk')
    def setUpClass(cls):
        super().setUpClass()
