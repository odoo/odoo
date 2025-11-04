from odoo.addons.account_edi.tests.common import AccountTestInvoicingCommon
from odoo.addons.point_of_sale.tests.test_generic_localization import TestGenericLocalization
from odoo.tests import tagged


@tagged('post_install', '-at_install', 'post_install_l10n')
class TestGenericCO(TestGenericLocalization):
    @classmethod
    @AccountTestInvoicingCommon.setup_country('co')
    def setUpClass(cls):
        super().setUpClass()
        cls.partner_a.vat = '/'  # So that we don't sent actual request as company

    def test_generic_localization(self):
        order, html_data = super().test_generic_localization()
        self.assertTrue(order.name in html_data)
