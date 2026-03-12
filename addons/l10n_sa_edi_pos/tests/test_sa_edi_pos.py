import json
from base64 import b64decode
from contextlib import contextmanager
from unittest.mock import patch

from odoo.tests import tagged

from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.addons.account_edi.tests.common import AccountEdiTestCommon
from odoo.addons.l10n_sa_edi.tests.common import AccountEdiTestCommon as SaAccountEdiTestCommon
from odoo.addons.point_of_sale.tests.common import TestPoSCommon
from odoo.addons.point_of_sale.tests.test_frontend import TestPointOfSaleHttpCommon
from odoo.addons.point_of_sale.tests.test_generic_localization import TestGenericLocalization


@tagged('post_install', '-at_install', 'post_install_l10n')
class TestGenericSAEdi(TestGenericLocalization):
    @classmethod
    @SaAccountEdiTestCommon.setup_edi_format('l10n_sa_edi.edi_sa_zatca')
    @AccountTestInvoicingCommon.setup_country('sa')
    def setUpClass(cls):
        super().setUpClass()
        cls.main_pos_config.journal_id._l10n_sa_load_edi_demo_data()
        cls.company.write({
            'name': 'Generic SA EDI',
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


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestUi(TestPointOfSaleHttpCommon):

    @classmethod
    @AccountEdiTestCommon.setup_country('sa')
    def setUpClass(cls):
        super().setUpClass()

    @patch('odoo.addons.l10n_sa_edi.models.account_journal.AccountJournal._l10n_sa_ready_to_submit_einvoices',
           new=lambda self: True)
    def test_ZATCA_invoice_not_mandatory_if_deposit(self):
        """
        Tests that the invoice is  not mandatory in POS payment for ZATCA if it's a deposit.
        """

        self.test_partner = self.env["res.partner"].create({"name": "AAA Partner"})
        self.start_tour(
            "/pos/ui?config_id=%d" % self.main_pos_config.id,
            'ZATCA_invoice_not_mandatory_if_deposit',
            login="pos_admin"
        )

    @patch('odoo.addons.l10n_sa_edi.models.account_journal.AccountJournal._l10n_sa_ready_to_submit_einvoices',
           new=lambda self: True)
    def test_ZATCA_invoice_mandatory_if_regular_order(self):
        """
        Tests that the invoice is mandatory in POS payment for ZATCA.
        Also is by default checked.
        """

        self.test_partner = self.env["res.partner"].create({"name": "AAA Partner"})
        self.start_tour(
            "/pos/ui?config_id=%d" % self.main_pos_config.id,
            'ZATCA_invoice_mandatory_if_regular_order',
            login="pos_admin",
        )


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestSAZATCAPosInvoice(TestPoSCommon):
    """Test that sync_from_ui with generate_pdf=False runs ZATCA synchronously but defers PDF."""

    @classmethod
    @SaAccountEdiTestCommon.setup_edi_format('l10n_sa_edi.edi_sa_zatca')
    @AccountTestInvoicingCommon.setup_country('sa')
    def setUpClass(cls):
        super().setUpClass()
        cls.config = cls.basic_config

        # Configure company for ZATCA
        sa_country = cls.env.ref('base.sa')
        state = cls.env['res.country.state'].create({
            'name': 'Riyadh',
            'code': 'RYD',
            'country_id': sa_country.id,
        })
        cls.env.company.write({
            'country_id': sa_country.id,
            'vat': '311111111111113',
            'street': 'Al Amir Mohammed Bin Abdul Aziz Street',
            'street2': 'Testomania',
            'city': 'المدينة المنورة',
            'zip': '42317',
            'state_id': state.id,
            'l10n_sa_edi_building_number': '1234',
            'phone': '+966 51 234 5678',
        })

        # Load ZATCA demo credentials on the invoice journal (used by ZATCA onboarding check)
        journal = cls.config.invoice_journal_id
        journal._l10n_sa_load_edi_demo_data()
        PCSID_data = json.loads(journal.l10n_sa_production_csid_json)
        cert = cls.env['certificate.certificate'].create({
            'name': 'PCSID Certificate',
            'content': b64decode(PCSID_data['binarySecurityToken']),
        })
        journal.l10n_sa_production_csid_certificate_id = cert

        # SA partner (simplified invoice — no B2B fields required)
        cls.sa_partner = cls.env['res.partner'].create({
            'name': 'SA Test Customer',
            'country_id': sa_country.id,
        })

        cls.sa_product = cls.create_product(
            'SA Product', cls.categ_basic, 100.0, tax_ids=cls.taxes['tax7'].ids
        )

    @contextmanager
    def with_pos_session(self):
        session = self.open_new_session(0.0)
        yield session
        session.post_closing_cash_details(0.0)
        session.close_session_from_ui()

    def test_generate_pdf_false_runs_zatca_skips_pdf(self):
        """
        When sync_from_ui is called with generate_pdf=False (set by the SA JS patch),
        _generate_pos_order_invoice must:
        - Process ZATCA EDI synchronously  →  edi_document.state == 'sent'
        - Skip PDF generation              →  invoice_pdf_report_id is False
        """
        ZATCA_PATCH = (
            'odoo.addons.l10n_sa_edi.models.account_edi_format'
            '.AccountEdiFormat._l10n_sa_post_zatca_edi'
        )
        with self.with_pos_session():
            order_data = self.create_ui_order_data(
                pos_order_lines_ui_args=[(self.sa_product, 1.0)],
                customer=self.sa_partner,
                is_invoiced=True,
            )
            with patch(ZATCA_PATCH, new=lambda __self, invoice: {invoice: {'success': True}}):
                results = self.env['pos.order'].with_context(generate_pdf=False).sync_from_ui([order_data])

        order = self.env['pos.order'].browse(results['pos.order'][0]['id'])
        invoice = order.account_move

        zatca_doc = invoice.edi_document_ids.filtered(
            lambda d: d.edi_format_id.code == 'sa_zatca'
        )
        self.assertTrue(zatca_doc, "ZATCA EDI document should exist after invoicing")
        self.assertEqual(zatca_doc.state, 'sent',
            "ZATCA EDI document must be processed synchronously during POS checkout")
        self.assertFalse(invoice.invoice_pdf_report_id,
            "PDF must not be generated during checkout — it is deferred to on-demand generation")
