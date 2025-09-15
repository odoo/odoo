from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.addons.l10n_sa_edi.tests.common import TestSaEdiCommon
from odoo.addons.point_of_sale.tests.test_generic_localization import TestGenericLocalization
from odoo.tests import tagged
from odoo.addons.point_of_sale.tests.test_frontend import TestPointOfSaleHttpCommon
from odoo.addons.account_edi.tests.common import AccountEdiTestCommon


@tagged('post_install', '-at_install', 'post_install_l10n')
class TestGenericSA(TestGenericLocalization, TestSaEdiCommon):
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


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestUi(TestPointOfSaleHttpCommon):

    @classmethod
    @AccountEdiTestCommon.setup_edi_format('l10n_sa_edi.edi_sa_zatca')
    @AccountEdiTestCommon.setup_country('sa')
    def setUpClass(cls):
        super().setUpClass()
        # Setup company
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
        })

    def test_sa_qr_is_shown(self):
        """
        Tests that the Saudi Arabia's timezone is applied on the QR code generated at the
        end of an order.
        """
        if self.env['ir.module.module']._get('l10n_sa_edi').state == 'installed':
            self.skipTest("The needed configuration for e-invoices is not available")
        self.main_pos_config.with_user(self.pos_admin).open_ui()
        self.start_tour("/pos/ui?config_id=%d" % self.main_pos_config.id, 'test_sa_qr_is_shown', login="pos_admin")
