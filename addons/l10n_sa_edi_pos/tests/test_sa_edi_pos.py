import json
from base64 import b64decode
from contextlib import contextmanager
from unittest.mock import patch

from odoo.fields import Command
from odoo.tests import tagged

from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.addons.l10n_sa_edi.tests.common import AccountEdiTestCommon, TestSaEdiCommon
from odoo.addons.point_of_sale.tests.common import TestPoSCommon
from odoo.addons.point_of_sale.tests.test_generic_localization import TestGenericLocalization


@tagged('post_install', '-at_install', 'post_install_l10n')
class TestGenericSAEdi(TestGenericLocalization):
    @classmethod
    @AccountEdiTestCommon.setup_edi_format('l10n_sa_edi.edi_sa_zatca')
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
class TestSaEdiPos(TestSaEdiCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.pos_config = cls.env['pos.config'].sudo().create({'name': 'SA Test POS'})
        cls.pos_session = cls.env['pos.session'].sudo().create({
            'config_id': cls.pos_config.id,
            'state': 'opened',
        })

    def test_accounting_user_can_read_invoice_with_pos_order(self):
        """
        Regression: an accounting admin without POS access should not get an
        AccessError when opening a customer invoice linked to a POS order.
        """
        invoice = self._create_test_invoice(
            move_type='out_invoice',
            partner_id=self.partner_sa,
            invoice_line_ids=[{'price_unit': 100.0, 'tax_ids': [self.tax_15.id]}],
        )

        # Link a pos.order to the invoice to trigger the code path
        self.env['pos.order'].sudo().create({
            'session_id': self.pos_session.id,
            'account_move': invoice.id,
            'amount_tax': 0.0,
            'amount_total': 100.0,
            'amount_paid': 100.0,
            'amount_return': 0.0,
        })

        # Create a user with accounting admin rights but no POS access
        accounting_user = self.env['res.users'].create({
            'name': 'Test Accountant No POS',
            'login': 'test_accountant_no_pos',
            'company_id': self.company.id,
            'company_ids': [Command.link(self.company.id)],
            'group_ids': [Command.link(self.env.ref('account.group_account_manager').id)],
        })

        edi_format = self.env.ref('l10n_sa_edi.edi_sa_zatca')

        # Simulate pos_settle_due being installed: it adds _is_settle_or_deposit to
        # pos.order.line, which is what enables the buggy code path. Without this
        # patch the hasattr() guard would short-circuit and the bug would not be hit.
        with patch(
            'odoo.addons.point_of_sale.models.pos_order.PosOrderLine._is_settle_or_deposit',
            new=lambda self: False,
            create=True,
        ):
            result = edi_format._move_has_settle_or_deposit_pos_order(invoice.with_user(accounting_user))
            self.assertFalse(result)


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestUi(TestGenericSAEdi):

    def make_payment(self, order, payment_method, amount):
        """ Make payment for the order using the given payment method.
        """
        payment_context = {"active_id": order.id, "active_ids": order.ids}
        return self.env['pos.make.payment'].with_context(**payment_context).create({
            'amount': amount,
            'payment_method_id': payment_method.id,
        }).check()

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

    @patch(
        "odoo.addons.l10n_sa_edi.models.account_journal.AccountJournal._l10n_sa_ready_to_submit_einvoices",
        new=lambda self: True,
    )
    def test_ZATCA_blocks_settle_due_and_sale_on_same_order(self):
        """
        Tests that the invoice is mandatory in POS payment for ZATCA.
        Also is by default checked.
        """
        if not self.env["ir.module.module"].search([("name", "=", "pos_settle_due"), ("state", "=", "installed")]):
            self.skipTest("pos_settle_due module is required for this test")

        self.customer_account_payment_method = self.env["pos.payment.method"].create(
            {
                "name": "Customer Account",
                "split_transactions": True,
            },
        )
        self.main_pos_config.write(
            {"payment_method_ids": [(4, self.customer_account_payment_method.id)]},
        )

        self.assertEqual(self.partner_a.total_due, 0)

        self.main_pos_config.with_user(self.pos_admin).open_ui()
        current_session = self.main_pos_config.current_session_id

        order = self.env["pos.order"].create(
            {
                "company_id": self.env.company.id,
                "session_id": current_session.id,
                "partner_id": self.partner_a.id,
                "lines": [
                    Command.create(
                        {
                            "product_id": self.whiteboard_pen.product_variant_id.id,
                            "price_unit": 20,
                            "discount": 0,
                            "qty": 1,
                            "price_subtotal": 10,
                            "tax_ids": [Command.link(self.tax_sale_a.id)],
                            "price_subtotal_incl": 23,
                        },
                    ),
                ],
                "amount_paid": 23,
                "amount_total": 23.0,
                "amount_tax": 3,
                "amount_return": 0.0,
                "to_invoice": True,
                "last_order_preparation_change": "{}",
            },
        )

        self.make_payment(order, self.customer_account_payment_method, 23)
        current_session.action_pos_session_closing_control()
        self.assertEqual(self.partner_a.total_due, 23)

        self.main_pos_config.open_ui()

        self.start_tour(
            "/pos/ui?config_id=%d" % self.main_pos_config.id,
            "ZATCA_blocks_settle_due_and_sale_on_same_order",
            login="accountman",
        )


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestSAZATCAPosInvoice(TestPoSCommon):
    """Test that sync_from_ui with generate_pdf=False runs ZATCA synchronously but defers PDF."""

    @classmethod
    @AccountEdiTestCommon.setup_edi_format('l10n_sa_edi.edi_sa_zatca')
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
