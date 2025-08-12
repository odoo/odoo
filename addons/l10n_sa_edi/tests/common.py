# coding: utf-8
import json
from base64 import b64decode

from odoo import Command
from odoo.tests import tagged
from odoo.addons.account_edi.tests.common import AccountEdiTestCommon


@tagged('post_install_l10n', '-at_install', 'post_install')
class TestSaEdiCommon(AccountEdiTestCommon):
    """
    Base test class for Saudi Arabia EDI functionality.

    Sets up test data for ZATCA (Saudi tax authority) compliance testing including:
    - Company with Saudi-specific fields
    - Partners (company and individual)
    - Products and taxes
    - XPath templates for XML comparison
    """

    @classmethod
    @AccountEdiTestCommon.setup_edi_format('l10n_sa_edi.edi_sa_zatca')
    @AccountEdiTestCommon.setup_chart_template('sa')
    @AccountEdiTestCommon.setup_country('sa')
    def setUpClass(cls):
        super().setUpClass()

        # Setup frequently used references
        cls.company = cls.company_data['company']
        cls.saudi_arabia = cls.env.ref('base.sa')
        cls.riyadh = cls._get_or_create_state('Riyadh', 'RUH', cls.saudi_arabia)

        # Setup test data
        cls._setup_company()
        cls._setup_branches()
        cls._setup_partners()
        cls._setup_products()
        cls._setup_taxes()
        cls._setup_journal()
        cls._setup_xpath_templates()

    @classmethod
    def _get_company_vals(cls, defaults=None):
        return {
            'name': 'SA Company Test',
            'email': 'info@company.saexample.com',
            'phone': '+966 51 234 5678',
            'vat': '311111111111113',
            # Address fields
            'street': 'Al Amir Mohammed Bin Abdul Aziz Street',
            'street2': 'Testomania',
            'city': 'المدينة المنورة',
            'zip': '42317',
            'country_id': cls.saudi_arabia.id,
            'state_id': cls.riyadh.id,
            # Saudi-specific fields
            'l10n_sa_edi_building_number': '1234',
            'l10n_sa_edi_plot_identification': '1234',
            'l10n_sa_edi_additional_identification_number': '2525252525252',
            'l10n_sa_edi_additional_identification_scheme': 'CRN',  # Commercial Registration Number
            **(defaults or {})
        }

    @classmethod
    def _setup_company(cls):
        """Configure the test company with Saudi Arabia specific settings."""
        cls.company.write(cls._get_company_vals())

    @classmethod
    def _setup_branches(cls):
        vals = cls._get_company_vals({"name": "SA Branch", "parent_id": cls.company.id})
        cls.sa_branch = cls._create_company(**vals)

    @classmethod
    def _setup_partners(cls):
        """Create test partners for different invoice types."""
        # Standard invoice partner (company)
        cls.partner_sa = cls._create_saudi_company_partner()

        # Simplified invoice partner (individual)
        cls.partner_sa_simplified = cls._create_saudi_individual_partner()

    @classmethod
    def _create_saudi_company_partner(cls):
        """Create a Saudi company partner with full ZATCA requirements."""
        return cls.env['res.partner'].create({
            'name': 'Saud Ahmed',
            'ref': 'Saudi Aramco',
            'company_type': 'company',
            'lang': 'en_US',
            # Contact info
            'email': 'saudi.aramco@example.com',
            'phone': '+966556666666',
            # Tax info
            'vat': '311111111111113',
            'l10n_sa_edi_additional_identification_scheme': 'CRN',
            'l10n_sa_edi_additional_identification_number': '353535353535353',
            # Address
            'street': '4557 King Salman St',
            'street2': 'Neighbor!',
            'city': 'Riyadh',
            'zip': '94538',
            'state_id': cls.riyadh.id,
            'country_id': cls.saudi_arabia.id,
            # Saudi-specific address fields
            'l10n_sa_edi_building_number': '12300',
            'l10n_sa_edi_plot_identification': '2323',
        })

    @classmethod
    def _create_saudi_individual_partner(cls):
        """Create a Saudi individual partner for simplified invoices."""
        return cls.env['res.partner'].create({
            'name': 'Mohammed Ali',
            'ref': 'Mohammed Ali',
            'company_type': 'person',
            'lang': 'en_US',
            'country_id': cls.saudi_arabia.id,
            'state_id': cls.riyadh.id,
            # Simplified invoices use different ID schemes
            'l10n_sa_edi_additional_identification_scheme': 'MOM',  # Momra License
            'l10n_sa_edi_additional_identification_number': '3123123213131',
        })

    @classmethod
    def _setup_products(cls):
        """Create test products."""
        cls.product_a = cls._create_product(name='Product A', standard_price=320.0, default_code='P0001')
        cls.product_b = cls._create_product(name='Product B', standard_price=15.8, default_code='P0002')
        cls.product_burger = cls._create_product(name='Burger', standard_price=265.0)

    @classmethod
    def _setup_taxes(cls):
        """Setup tax references."""
        # Standard 15% VAT in Saudi Arabia
        cls.tax_15 = cls.env['account.tax'].search([
            ('company_id', '=', cls.company.id),
            ('amount', '=', 15.0)
        ], limit=1)

    @classmethod
    def _setup_journal(cls):
        """Setup and configure the sales journal."""
        cls.customer_invoice_journal = cls.env['account.journal'].search([
            ('company_id', '=', cls.company.id),
            ('type', '=', 'sale')
        ], limit=1)

        # Load ZATCA demo data (certificates, etc.)
        cls.customer_invoice_journal._l10n_sa_load_edi_demo_data()
        PCSID_Data = json.loads(cls.customer_invoice_journal.l10n_sa_production_csid_json)
        pcsid_certificate = cls.env['certificate.certificate'].create({
            'name': 'PCSID Certificate',
            'content': b64decode(PCSID_Data['binarySecurityToken']),
        })
        cls.customer_invoice_journal.l10n_sa_production_csid_certificate_id = pcsid_certificate

    @classmethod
    def _setup_xpath_templates(cls):
        """
        Setup XPath templates for XML testing.

        These remove or replace dynamic elements (IDs, UUIDs) that change
        between test runs to allow XML comparison.
        """
        cls.remove_ubl_extensions_xpath = '''<xpath expr="//*[local-name()='UBLExtensions']" position="replace"/>'''

        # Common replacements for all document types
        common_replacements = '''
            <xpath expr="(//*[local-name()='Invoice']/*[local-name()='ID'])[1]" position="replace">
                <cbc:ID xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2">___ignore___</cbc:ID>
            </xpath>
            <xpath expr="(//*[local-name()='Invoice']/*[local-name()='UUID'])[1]" position="replace">
                <cbc:UUID xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2">___ignore___</cbc:UUID>
            </xpath>
            <xpath expr="(//*[local-name()='Contact']/*[local-name()='ID'])[1]" position="replace">
                <cbc:ID xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2">___ignore___</cbc:ID>
            </xpath>
            <xpath expr="(//*[local-name()='Contact']/*[local-name()='ID'])[2]" position="replace">
                <cbc:ID xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2">___ignore___</cbc:ID>
            </xpath>
        '''

        # Invoice-specific replacements
        cls.invoice_applied_xpath = common_replacements + '''
            <xpath expr="//*[local-name()='PaymentMeans']/*[local-name()='InstructionID']" position="replace">
                <cbc:InstructionID xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2">___ignore___</cbc:InstructionID>
            </xpath>
            <xpath expr="(//*[local-name()='PaymentMeans']/*[local-name()='PaymentID'])" position="replace">
                <cbc:PaymentID xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2">___ignore___</cbc:PaymentID>
            </xpath>
            <xpath expr="//*[local-name()='InvoiceLine']/*[local-name()='ID']" position="replace">
                <cbc:ID xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2">___ignore___</cbc:ID>
            </xpath>
        '''

        # Credit note specific replacements
        cls.credit_note_applied_xpath = common_replacements + '''
            <xpath expr="(//*[local-name()='InvoiceDocumentReference']/*[local-name()='ID'])[1]" position="replace">
                <cbc:ID xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2">___ignore___</cbc:ID>
            </xpath>
            <xpath expr="(//*[local-name()='PaymentMeans']/*[local-name()='InstructionNote'])" position="replace">
                <cbc:InstructionNote xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2">___ignore___</cbc:InstructionNote>
            </xpath>
            <xpath expr="(//*[local-name()='PaymentMeans']/*[local-name()='PaymentID'])" position="replace">
                <cbc:PaymentID xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2">___ignore___</cbc:PaymentID>
            </xpath>
            <xpath expr="//*[local-name()='InvoiceLine']/*[local-name()='ID']" position="replace">
                <cbc:ID xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2">___ignore___</cbc:ID>
            </xpath>
        '''

        # Debit note specific replacements
        cls.debit_note_applied_xpath = common_replacements + '''
            <xpath expr="(//*[local-name()='InvoiceDocumentReference']/*[local-name()='ID'])[1]" position="replace">
                <cbc:ID xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2">___ignore___</cbc:ID>
            </xpath>
            <xpath expr="//*[local-name()='InvoiceLine']/*[local-name()='ID']" position="replace">
                <cbc:ID xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2">___ignore___</cbc:ID>
            </xpath>
            <xpath expr="//*[local-name()='PaymentMeans']/*[local-name()='InstructionID']" position="replace">
                <cbc:InstructionID xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2">___ignore___</cbc:InstructionID>
            </xpath>
            <xpath expr="(//*[local-name()='PaymentMeans']/*[local-name()='PaymentID'])" position="replace">
                <cbc:PaymentID xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2">___ignore___</cbc:PaymentID>
            </xpath>
            <xpath expr="(//*[local-name()='PaymentMeans']/*[local-name()='InstructionNote'])" position="replace">
                <cbc:InstructionNote xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2">___ignore___</cbc:InstructionNote>
            </xpath>
        '''

    @classmethod
    def _get_or_create_state(cls, name, code, country):
        """Ensure a state exists for the given country."""
        state = cls.env['res.country.state'].search([
            ('code', '=', code),
            ('country_id', '=', country.id)
        ], limit=1)

        if not state:
            state = cls.env['res.country.state'].create({
                'name': name,
                'code': code,
                'country_id': country.id
            })

        return state

    # Helper methods for creating documents
    def _create_test_invoice(
        self,
        name="",
        move_type="out_invoice",
        company_id=None,
        partner_id=None,
        invoice_date='2025-01-01',
        invoice_date_due='2025-01-01',
        currency_id=None,
        invoice_line_ids=[]):
        """
        Create a draft invoice with the given parameters.
        """
        def _create_invoice_line(line):
            vals = {
                'price_unit': line.get('price_unit', 0.0),
                'quantity': line.get('quantity', 1),
                'tax_ids': line.get('tax_ids', []),
            }
            if product_id := line.get('product_id'):
                vals['product_id'] = product_id
            if name := line.get('name'):
                vals['name'] = name
            return Command.create(vals)
        vals = {
            'name': name,
            'move_type': move_type,
            'company_id': (company_id or self.company).id,
            'partner_id': partner_id.id,
            'invoice_date': invoice_date,
            'invoice_date_due': invoice_date_due,
            'currency_id': (currency_id or self.company.currency_id).id,
            'invoice_line_ids': [
                _create_invoice_line(line) for line in invoice_line_ids
            ],
        }
        return self.env['account.move'].create(vals)

    def _create_debit_note(
        self,
        name="",
        move_type="out_invoice",
        company_id=None,
        partner_id=None,
        invoice_date='2025-01-01',
        invoice_date_due='2025-01-01',
        currency_id=None,
        invoice_line_ids=[],
        reason="BR-KSA-17-reason-5"):
        """
        Create a draft debit note from the given invoice values.
        """
        # Create and post the original invoice
        invoice = self._create_test_invoice(
            name=name,
            move_type=move_type,
            company_id=company_id,
            partner_id=partner_id,
            invoice_date=invoice_date,
            invoice_date_due=invoice_date_due,
            currency_id=currency_id,
            invoice_line_ids=invoice_line_ids)
        invoice.action_post()

        # Create debit note via wizard
        debit_note_wizard = self.env['account.debit.note'].with_context({
            'active_ids': [invoice.id],
            'active_model': 'account.move',
            'default_copy_lines': True
        }).create({
            'l10n_sa_reason': reason,
        })
        res = debit_note_wizard.create_debit()

        return self.env['account.move'].browse(res.get('res_id', []))

    def _create_credit_note(
        self,
        name="",
        move_type="out_invoice",
        company_id=None,
        partner_id=None,
        invoice_date='2025-01-01',
        invoice_date_due='2025-01-01',
        currency_id=None,
        invoice_line_ids=[],
        reason='BR-KSA-17-reason-5'):
        """
        Create a draft credit note from the given invoice values.
        """
        # Create and post the original invoice
        invoice = self._create_test_invoice(
            name=name,
            move_type=move_type,
            company_id=company_id,
            partner_id=partner_id,
            invoice_date=invoice_date,
            invoice_date_due=invoice_date_due,
            currency_id=currency_id,
            invoice_line_ids=invoice_line_ids)
        invoice.action_post()

        # Create credit note via reversal wizard
        move_reversal = self.env['account.move.reversal'].with_context({
            'active_model': 'account.move',
            'active_ids': invoice.ids
        }).create({
            'l10n_sa_reason': reason,
            'journal_id': invoice.journal_id.id,
        })
        reversal = move_reversal.reverse_moves()

        return self.env['account.move'].browse(reversal['res_id'])
