from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.addons.account_edi.tests.common import AccountEdiTestCommon
from odoo.addons.point_of_sale.tests.test_generic_localization import TestGenericLocalization
from odoo.tests import tagged


@tagged('post_install', '-at_install', 'post_install_l10n')
class TestGenericGCC(TestGenericLocalization):
    @classmethod
    @AccountEdiTestCommon.setup_edi_format('l10n_sa_edi.edi_sa_zatca')
    @AccountTestInvoicingCommon.setup_country('sa')
    def setUpClass(cls):
        super().setUpClass()
        cls.main_pos_config.company_id.name = 'Generic SA'
        cls.main_pos_config.journal_id._l10n_sa_load_edi_demo_data()
        cls.company.write({
            'name': 'SA Company Test',
            'email': 'info@company.saexample.com',
            'phone': '+966 51 234 5678',
            'street2': 'Testomania',
            'vat': '311111111111113',
            'state_id': cls.env['res.country.state'].create({
                'name': 'Riyadh',
                'code': 'RYA',
                'country_id': cls.company.country_id.id
            }),
            'street': 'Al Amir Mohammed Bin Abdul Aziz Street',
            'city': 'المدينة المنورة',
            'zip': '42317',
            'l10n_sa_edi_building_number': '1234',
        })

    def test_generic_localization(self):
        if self.env['ir.module.module']._get('l10n_sa_edi').state != 'installed':
            self.skipTest("l10n_sa_edi is not installed")
        super().test_generic_localization()
