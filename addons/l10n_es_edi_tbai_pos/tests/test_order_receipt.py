# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo.tests import tagged
from odoo.addons.point_of_sale.tests.test_order_receipt import TestPosOrderReceipt
from odoo.addons.account.tests.common import AccountTestInvoicingCommon


@tagged('post_install', '-at_install', 'post_install_l10n')
class TestOrderReceiptL10n(TestPosOrderReceipt):
    @classmethod
    @AccountTestInvoicingCommon.setup_country('es')
    def setUpClass(self):
        super().setUpClass()
        self.company.l10n_es_tbai_tax_agency = 'bizkaia'
        self.key_to_skip['image'].append('l10n_es_pos_tbai_qrsrc')

    def test_receipt_data(self):
        super().test_receipt_data()
