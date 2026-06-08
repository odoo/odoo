# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo.tests import tagged
from odoo.addons.point_of_sale.tests.test_order_receipt import TestPosOrderReceipt
from odoo.addons.account.tests.common import AccountTestInvoicingCommon


@tagged('post_install', '-at_install', 'post_install_l10n')
class TestOrderReceiptL10n(TestPosOrderReceipt):
    @classmethod
    @AccountTestInvoicingCommon.setup_country('sa')
    def setUpClass(cls):
        super().setUpClass()
        if cls.env['ir.module.module']._get('l10n_sa_edi').state == 'installed':
            cls.skipTest(cls, "l10n_sa_edi should not be installed")
        cls.main_pos_config.company_id.name = 'Generic GCC'
        cls.company.write({
            'email': 'info@company.saexample.com',
            'phone': '+966 51 234 5678',
            'street2': 'Testomania',
            'vat': '311111111111113',
            'state_id': cls.env['res.country.state'].create({
                'name': 'Riyadh',
                'code': 'RYA',
                'country_id': cls.company.country_id.id
            }),
            'street': 'Al Amir Mohammed Bin '
            'Abdul Aziz Street',
            'city': 'المدينة المنورة',
            'zip': '42317',
        })

    def test_receipt_data(self):
        super().test_receipt_data()
