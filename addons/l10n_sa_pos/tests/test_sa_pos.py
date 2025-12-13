from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.addons.point_of_sale.tests.common import TestPoSCommon
from odoo.addons.point_of_sale.tests.test_generic_localization import TestGenericLocalization
from odoo.tests import tagged
from odoo.addons.point_of_sale.tests.test_frontend import TestPointOfSaleHttpCommon
from odoo.addons.account_edi.tests.common import AccountEdiTestCommon


@tagged('post_install', '-at_install', 'post_install_l10n')
class TestGenericSA(TestGenericLocalization):
    @classmethod
    @AccountTestInvoicingCommon.setup_country('sa')
    def setUpClass(cls):
        super().setUpClass()
        if cls.env['ir.module.module']._get('l10n_sa_edi').state == 'installed':
            cls.skipTest(cls, "l10n_sa_edi should not be installed")
        cls.main_pos_config.company_id.name = 'Generic SA'
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


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestSaPosInvoice(TestPoSCommon, TestPointOfSaleHttpCommon):

    def test_consolidate_invoices_for_same_customer(self):
        """
        Test that consolidated invoicing for multiple POS orders of the same customer
        succeeds and sets the confirmation datetime for a Saudi Arabia company.
        """
        self.config = self.basic_config
        self.env.company.country_id = self.env.ref('base.sa')

        self.open_new_session()
        pos_orders = sum(self._create_orders([
            {
                'pos_order_lines_ui_args': [(self.product_a, 1)],
                'customer': self.customer,
                'is_invoiced': False,
            }
            for _ in range(2)
        ]).values(), self.env['pos.order'])

        self.env['pos.make.invoice'].create({"consolidated_billing": True}).with_context({
            "active_ids": pos_orders.ids
        }).action_create_invoices()
        invoice = pos_orders.account_move

        self.assertTrue(invoice, "A consolidated invoice should have been created")
        self.assertTrue(
            invoice.l10n_sa_confirmation_datetime,
            "The consolidated invoice should have l10n_sa_confirmation_datetime set"
        )
