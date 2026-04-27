from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.addons.point_of_sale.tests.test_generic_localization import TestGenericLocalization
from odoo.tests import tagged


@tagged('post_install', '-at_install', 'post_install_l10n')
class TestGenericPL(TestGenericLocalization):
    @classmethod
    @AccountTestInvoicingCommon.setup_country('pl')
    def setUpClass(cls):
        super().setUpClass()
