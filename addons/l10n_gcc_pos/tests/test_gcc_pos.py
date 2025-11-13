from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.addons.point_of_sale.tests.test_generic_localization import TestGenericLocalization
from odoo.tests import tagged


@tagged('post_install', '-at_install', 'post_install_l10n')
class TestGenericGCC(TestGenericLocalization):
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
            'street': 'Al Amir Mohammed Bin Abdul Aziz Street',
            'city': 'المدينة المنورة',
            'zip': '42317',
        })
