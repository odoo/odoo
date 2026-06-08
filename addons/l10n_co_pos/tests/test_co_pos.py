from unittest.mock import patch

from odoo.addons.account_edi.tests.common import AccountTestInvoicingCommon
from odoo.addons.point_of_sale.tests.test_generic_localization import TestGenericLocalization
from odoo.tests import tagged


@tagged('post_install', 'post_install_l10n')
class TestGenericCO(TestGenericLocalization):
    @classmethod
    @AccountTestInvoicingCommon.setup_country('co')
    def setUpClass(cls):
        super().setUpClass()
        cls.partner_a.vat = '/'  # So that we don't sent actual request as company

    def test_generic_localization(self):
        if self.env['ir.module.module']._get('l10n_co_edi_pos').state == 'installed':
            with patch.object(self.registry['account.move'], attribute='_generate_and_send', return_value={}):
                order, html_data = super().test_generic_localization()
        else:
            order, html_data = super().test_generic_localization()

        self.assertTrue(order.name in html_data)
