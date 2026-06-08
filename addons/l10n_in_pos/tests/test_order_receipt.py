# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo.tests import tagged
from odoo.addons.point_of_sale.tests.test_order_receipt import TestPosOrderReceipt
from odoo.addons.account.tests.common import AccountTestInvoicingCommon


@tagged('post_install', '-at_install', 'post_install_l10n')
class TestOrderReceiptL10n(TestPosOrderReceipt):
    @classmethod
    @AccountTestInvoicingCommon.setup_country('in')
    def setUpClass(cls):
        super().setUpClass()
        cls.state_in_gj = cls.env.ref('base.state_in_gj')
        cls.main_pos_config.company_id.write({
            'name': "Default Company",
            'state_id': cls.state_in_gj.id,
            'vat': "24AAGCC7144L6ZE",
            'street': "Khodiyar Chowk",
            'street2': "Sala Number 3",
            'city': "Amreli",
            'zip': "365220",
        })
        cls.example_simple_product.write({
            'l10n_in_hsn_code': '1111',
        })

    def test_receipt_data(self):
        super().test_receipt_data()
