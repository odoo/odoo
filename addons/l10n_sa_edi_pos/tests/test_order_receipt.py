# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo.tests import tagged
from odoo.addons.point_of_sale.tests.test_order_receipt import TestPosOrderReceipt
from odoo.addons.account_edi.tests.common import AccountTestInvoicingCommon
from odoo.addons.l10n_sa_edi.tests.common import AccountEdiTestCommon


@tagged('post_install', '-at_install', 'post_install_l10n')
class TestOrderReceiptL10n(TestPosOrderReceipt):
    @classmethod
    @AccountEdiTestCommon.setup_edi_format('l10n_sa_edi.edi_sa_zatca')
    @AccountTestInvoicingCommon.setup_country('sa')
    def setUpClass(self):
        super().setUpClass()
        self.main_pos_config.journal_id._l10n_sa_load_edi_test_data()
        self.company.write({
            'name': 'Generic SA EDI',
            'email': 'info@company.saexample.com',
            'phone': '+966 51 234 5678',
            'street2': 'Testomania',
            'vat': '311111111111113',
            'state_id': self.env['res.country.state'].create({
                'name': 'Riyadh',
                'code': 'RYA',
                'country_id': self.company.country_id.id,
            }),
            'street': 'Al Amir Mohammed Bin Abdul Aziz Street',
            'city': 'المدينة المنورة',
            'zip': '42317',
            'l10n_sa_edi_building_number': '1234',
        })
        self.key_to_skip['image'].append('sa_qr_code')

    def test_receipt_data(self):
        super().test_receipt_data()
