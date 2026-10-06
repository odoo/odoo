from lxml import etree

from odoo import fields
from odoo.tests import tagged

from .common import TestL10nFrPdpCommon


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestCreditNoteReferences(TestL10nFrPdpCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        model = cls.env['ir.model']._get('account.move')
        studio_fields = cls.env['ir.model.fields'].with_context(studio=True)
        studio_fields.create([
            {
                'name': name,
                'model_id': model.id,
                'ttype': field_type,
            }
            for name, field_type in (
                ('x_studio_peppol_contract_document_reference_id', 'char'),
                ('x_studio_peppol_invoice_previous_date', 'date'),
                ('x_studio_peppol_invoice_period_start_date', 'date'),
                ('x_studio_peppol_invoice_period_end_date', 'date'),
            )
            if name not in cls.env['account.move']._fields
        ])

    def _create_standalone_credit_note(self, **values):
        credit_note = self._create_french_invoice(move_type='out_refund', **values)
        credit_note.action_post()
        return credit_note

    def test_export_historical_credit_note(self):
        credit_note = self._create_standalone_credit_note(
            x_studio_peppol_contract_document_reference_id='PAPER-2020-0042',
            x_studio_peppol_invoice_previous_date='2020-04-15',
        )

        xml, errors = self.env['account.edi.xml.ubl_21_fr']._export_invoice(credit_note)
        tree = etree.fromstring(xml)

        self.assertFalse(errors)
        self.assertEqual(tree.findtext('./{*}CreditNoteTypeCode'), '381')
        self.assertEqual(
            tree.findtext('./{*}BillingReference/{*}InvoiceDocumentReference/{*}ID'),
            'PAPER-2020-0042',
        )
        self.assertEqual(
            tree.findtext('./{*}BillingReference/{*}InvoiceDocumentReference/{*}IssueDate'),
            '2020-04-15',
        )
        self.assertIsNone(tree.find('./{*}ContractDocumentReference'))

    def test_export_global_discount_credit_note(self):
        credit_note = self._create_standalone_credit_note(
            x_studio_peppol_contract_document_reference_id='REBATE-2024',
            x_studio_peppol_invoice_period_start_date='2024-01-01',
            x_studio_peppol_invoice_period_end_date='2024-12-31',
        )

        xml, errors = self.env['account.edi.xml.ubl_21_fr']._export_invoice(credit_note)
        tree = etree.fromstring(xml)

        self.assertFalse(errors)
        self.assertEqual(tree.findtext('./{*}CreditNoteTypeCode'), '262')
        self.assertEqual(
            tree.findtext('./{*}ContractDocumentReference/{*}ID'),
            'REBATE-2024',
        )
        self.assertEqual(tree.findtext('./{*}InvoicePeriod/{*}StartDate'), '2024-01-01')
        self.assertEqual(tree.findtext('./{*}InvoicePeriod/{*}EndDate'), '2024-12-31')
        self.assertIsNone(tree.find('./{*}BillingReference'))

    def test_reject_incomplete_or_conflicting_standalone_reference(self):
        credit_note = self._create_french_invoice(move_type='out_refund')
        builder = self.env['account.edi.xml.ubl_21_fr']
        combinations = (
            ({}, True),
            ({'x_studio_peppol_contract_document_reference_id': 'REFERENCE'}, True),
            ({'x_studio_peppol_contract_document_reference_id': 'REFERENCE',
              'x_studio_peppol_invoice_period_start_date': '2024-01-01'}, True),
            ({'x_studio_peppol_contract_document_reference_id': 'REFERENCE',
              'x_studio_peppol_invoice_period_end_date': '2024-12-31'}, True),
            ({'x_studio_peppol_contract_document_reference_id': 'REFERENCE',
              'x_studio_peppol_invoice_previous_date': '2020-04-15'}, False),
            ({'x_studio_peppol_contract_document_reference_id': 'REFERENCE',
              'x_studio_peppol_invoice_period_start_date': '2024-01-01',
              'x_studio_peppol_invoice_period_end_date': '2024-12-31'}, False),
            ({'x_studio_peppol_contract_document_reference_id': 'REFERENCE',
              'x_studio_peppol_invoice_previous_date': '2020-04-15',
              'x_studio_peppol_invoice_period_start_date': '2024-01-01',
              'x_studio_peppol_invoice_period_end_date': '2024-12-31'}, True),
        )

        for values, should_fail in combinations:
            with self.subTest(values=values):
                credit_note.write({
                    'x_studio_peppol_contract_document_reference_id': False,
                    'x_studio_peppol_invoice_previous_date': False,
                    'x_studio_peppol_invoice_period_start_date': False,
                    'x_studio_peppol_invoice_period_end_date': False,
                    **values,
                })
                vals = builder._export_invoice_vals(credit_note)
                constraints = builder._export_invoice_constraints(credit_note, vals)
                self.assertEqual('ubl_21_fr_refund_invoice_reference' in constraints, should_fail)

    def test_flow_10_maps_global_discount_to_credit_note(self):
        credit_note = self._create_standalone_credit_note(
            x_studio_peppol_contract_document_reference_id='REBATE-2024',
            x_studio_peppol_invoice_period_start_date='2024-01-01',
            x_studio_peppol_invoice_period_end_date='2024-12-31',
        )
        builder = self.env['pdp.flow.10.xml.builder']
        invoice_node = {}

        builder._invoice_add_referenced_documents(invoice_node, credit_note)
        flow = self.env['l10n.fr.pdp.reports.flow'].new({
            'period_start': '2025-02-01',
            'period_end': '2025-02-28',
        })
        builder._invoice_add_invoice_period(invoice_node, credit_note, flow)

        self.assertEqual(builder._get_move_typecode(credit_note), '381')
        self.assertEqual(invoice_node['ReferencedDocument'], [{
            'ID': {'_text': 'REBATE-2024'},
            'IssueDate': {'_text': '20240101'},
        }])
        self.assertEqual(invoice_node['InvoicePeriod'], {
            'StartDate': {'_text': '20240101'},
            'EndDate': {'_text': '20241231'},
        })

    def test_flow_10_historical_and_linked_credit_notes(self):
        builder = self.env['pdp.flow.10.xml.builder']
        historical = self._create_standalone_credit_note(
            x_studio_peppol_contract_document_reference_id='PAPER-2020-0042',
            x_studio_peppol_invoice_previous_date='2020-04-15',
        )
        invoice_node = {}
        builder._invoice_add_referenced_documents(invoice_node, historical)
        self.assertEqual(invoice_node['ReferencedDocument'], [{
            'ID': {'_text': 'PAPER-2020-0042'},
            'IssueDate': {'_text': '20200415'},
        }])

        original = self._create_french_invoice(date='2017-02-01')
        original.action_post()
        linked = original._reverse_moves([{'date': '2017-02-02', 'invoice_date': '2017-02-02'}])
        linked.action_post()
        linked.write({
            'x_studio_peppol_contract_document_reference_id': 'UNRELATED',
            'x_studio_peppol_invoice_period_start_date': '2024-01-01',
            'x_studio_peppol_invoice_period_end_date': '2024-12-31',
        })
        xml, errors = self.env['account.edi.xml.ubl_21_fr']._export_invoice(linked)
        tree = etree.fromstring(xml)
        self.assertFalse(errors)
        self.assertEqual(tree.findtext('./{*}CreditNoteTypeCode'), '381')
        self.assertEqual(tree.findtext('./{*}BillingReference/{*}InvoiceDocumentReference/{*}ID'), original.name)

        invoice_node = {}
        builder._invoice_add_referenced_documents(invoice_node, linked)
        self.assertEqual(invoice_node['ReferencedDocument'], [{
            'ID': {'_text': original.name},
            'IssueDate': {'_text': '20170101'},
        }])

    def test_vendor_credit_note_reference_is_only_required_in_flow_10(self):
        credit_note = self._create_french_invoice(
            move_type='in_refund',
            partner_id=self.partner_b.id,
        )
        credit_note.action_post()
        self.assertFalse(credit_note._get_l10n_fr_pdp_errors())

        credit_note.l10n_fr_pdp_flow_10_operation_type = 'purchase'
        credit_note.l10n_fr_pdp_flow_10_report_type = 'transaction'
        self.assertTrue(any(
            'x_studio_peppol_invoice_previous_date' in error
            for error in credit_note._get_l10n_fr_pdp_errors()
        ))

    def test_correcting_posted_credit_note_refreshes_flow_10_error(self):
        # Use real Flow 10 reporting: a forced report type can be reset during recomputation.
        self.proxy_user.company_id = self.company
        self.company.write({
            'account_fiscal_country_id': self.env.ref('base.fr').id,
            'currency_id': self.env.ref('base.EUR').id,
            'l10n_fr_pdp_annuaire_start_date': '2025-01-01',
            'l10n_fr_pdp_periodicity': 'normal_monthly',
            'l10n_fr_pdp_send_to_ppf': True,
        })
        self.company._compute_account_peppol_edi_user()
        self.company._compute_l10n_fr_f10_enable_reporting()
        credit_note = self._create_standalone_credit_note(
            partner_id=self.partner_b.id,
            invoice_date='2025-02-05',
            date='2025-02-05',
        )
        self.assertEqual(credit_note.l10n_fr_pdp_flow_10_report_type, 'transaction')
        self.assertTrue(credit_note.l10n_fr_pdp_has_error)
        self.assertEqual(credit_note.l10n_fr_pdp_status, 'error')

        credit_note.write({
            'x_studio_peppol_contract_document_reference_id': 'PAPER-2020-0042',
            'x_studio_peppol_invoice_previous_date': '2020-04-15',
        })
        self.env.flush_all()
        credit_note.invalidate_recordset(['l10n_fr_pdp_has_error', 'l10n_fr_pdp_status'])

        self.assertFalse(credit_note._get_l10n_fr_pdp_errors())
        self.assertFalse(credit_note.l10n_fr_pdp_has_error)
        self.assertEqual(credit_note.l10n_fr_pdp_status, 'pending')

        credit_note.write({
            'x_studio_peppol_invoice_previous_date': False,
            'x_studio_peppol_invoice_period_start_date': '2024-01-01',
            'x_studio_peppol_invoice_period_end_date': '2024-01-01',
        })
        self.assertTrue(credit_note.l10n_fr_pdp_has_error)
        self.assertEqual(credit_note.l10n_fr_pdp_status, 'error')

        credit_note.x_studio_peppol_invoice_period_end_date = '2024-12-31'
        self.assertFalse(credit_note.l10n_fr_pdp_has_error)
        self.assertEqual(credit_note.l10n_fr_pdp_status, 'pending')

    def test_flow_10_rejects_invalid_global_discount_period(self):
        credit_note = self._create_standalone_credit_note(
            partner_id=self.partner_b.id,
            x_studio_peppol_contract_document_reference_id='REBATE-2024',
            x_studio_peppol_invoice_period_start_date='2024-01-01',
            x_studio_peppol_invoice_period_end_date='2024-01-01',
        )
        credit_note.l10n_fr_pdp_flow_10_operation_type = 'sale'
        credit_note.l10n_fr_pdp_flow_10_report_type = 'transaction'

        for period_end, should_fail in (
            ('2023-12-31', True),
            ('2024-01-01', True),
            ('2024-01-02', False),
        ):
            with self.subTest(period_end=period_end):
                credit_note.x_studio_peppol_invoice_period_end_date = period_end
                errors = credit_note._get_l10n_fr_pdp_errors()
                self.assertEqual(
                    any('invoice period end date must be after' in error for error in errors),
                    should_fail,
                )

        credit_note.x_studio_peppol_invoice_period_start_date = '1999-01-01'
        self.assertTrue(any(
            'invoice period dates must be between 2000 and 2099' in error
            for error in credit_note._get_l10n_fr_pdp_errors()
        ))

    def test_flow_10_rejects_invalid_studio_reference(self):
        credit_note = self._create_standalone_credit_note(
            partner_id=self.partner_b.id,
            x_studio_peppol_contract_document_reference_id='PAPER.INVALID',
            x_studio_peppol_invoice_previous_date='1999-04-15',
        )
        credit_note.l10n_fr_pdp_flow_10_operation_type = 'sale'
        credit_note.l10n_fr_pdp_flow_10_report_type = 'transaction'

        errors = credit_note._get_l10n_fr_pdp_errors()

        self.assertTrue(any('previous document reference' in error for error in errors))
        self.assertTrue(any('previous invoice date must be between 2000 and 2099' in error for error in errors))

    def test_import_ubl_credit_note_references(self):
        builder = self.env['account.edi.xml.ubl_21_fr']
        credit_note = self._create_french_invoice(move_type='in_refund')
        tree = etree.fromstring(b'''\
            <CreditNote xmlns="urn:oasis:names:specification:ubl:schema:xsd:CreditNote-2"
                        xmlns:cac="urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2"
                        xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2">
                <cbc:CreditNoteTypeCode>262</cbc:CreditNoteTypeCode>
                <cac:InvoicePeriod>
                    <cbc:StartDate>2024-01-01</cbc:StartDate>
                    <cbc:EndDate>2024-12-31</cbc:EndDate>
                </cac:InvoicePeriod>
                <cac:ContractDocumentReference><cbc:ID>REBATE-2024</cbc:ID></cac:ContractDocumentReference>
            </CreditNote>
        ''')

        builder._import_fill_invoice_form(credit_note, tree, 1)

        self.assertRecordValues(credit_note, [{
            'x_studio_peppol_contract_document_reference_id': 'REBATE-2024',
            'x_studio_peppol_invoice_previous_date': False,
            'x_studio_peppol_invoice_period_start_date': fields.Date.to_date('2024-01-01'),
            'x_studio_peppol_invoice_period_end_date': fields.Date.to_date('2024-12-31'),
        }])

    def test_import_ubl_historical_credit_note(self):
        credit_note = self._create_french_invoice(move_type='in_refund')
        tree = etree.fromstring(b'''\
            <CreditNote xmlns="urn:oasis:names:specification:ubl:schema:xsd:CreditNote-2"
                        xmlns:cac="urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2"
                        xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2">
                <cbc:CreditNoteTypeCode>381</cbc:CreditNoteTypeCode>
                <cac:ContractDocumentReference><cbc:ID>CONTRACT-OTHER</cbc:ID></cac:ContractDocumentReference>
                <cac:BillingReference>
                    <cac:InvoiceDocumentReference>
                        <cbc:ID>PAPER-2020-0042</cbc:ID>
                        <cbc:IssueDate>2020-04-15</cbc:IssueDate>
                    </cac:InvoiceDocumentReference>
                </cac:BillingReference>
            </CreditNote>
        ''')

        self.env['account.edi.xml.ubl_21_fr']._import_fill_invoice_form(credit_note, tree, 1)

        self.assertRecordValues(credit_note, [{
            'x_studio_peppol_contract_document_reference_id': 'PAPER-2020-0042',
            'x_studio_peppol_invoice_previous_date': fields.Date.to_date('2020-04-15'),
        }])

    def test_import_facturx_credit_note_references(self):
        builder = self.env['account.edi.xml.cii']
        credit_note = self._create_french_invoice(move_type='in_refund')
        tree = etree.fromstring(b'''\
            <CrossIndustryInvoice xmlns="urn:un:unece:uncefact:data:standard:CrossIndustryInvoice:100"
                                  xmlns:ram="urn:un:unece:uncefact:data:standard:ReusableAggregateBusinessInformationEntity:100"
                                  xmlns:udt="urn:un:unece:uncefact:data:standard:UnqualifiedDataType:100">
                <ExchangedDocument><ram:TypeCode>381</ram:TypeCode></ExchangedDocument>
                <SupplyChainTradeTransaction>
                    <ram:ApplicableHeaderTradeSettlement>
                        <ram:InvoiceReferencedDocument>
                            <ram:IssuerAssignedID>PAPER-2020-0042</ram:IssuerAssignedID>
                            <ram:FormattedIssueDateTime>
                                <udt:DateTimeString format="102">20200415</udt:DateTimeString>
                            </ram:FormattedIssueDateTime>
                        </ram:InvoiceReferencedDocument>
                    </ram:ApplicableHeaderTradeSettlement>
                </SupplyChainTradeTransaction>
            </CrossIndustryInvoice>
        ''')

        self.assertEqual(builder._get_import_document_amount_sign(tree), ('refund', 1))
        builder._import_fill_invoice_form(credit_note, tree, 1)

        self.assertRecordValues(credit_note, [{
            'x_studio_peppol_contract_document_reference_id': 'PAPER-2020-0042',
            'x_studio_peppol_invoice_previous_date': fields.Date.to_date('2020-04-15'),
            'x_studio_peppol_invoice_period_start_date': False,
            'x_studio_peppol_invoice_period_end_date': False,
        }])

    def test_facturx_global_discount_is_imported_as_refund(self):
        builder = self.env['account.edi.xml.cii']
        credit_note = self._create_french_invoice(move_type='in_refund')
        tree = etree.fromstring(b'''\
            <CrossIndustryInvoice xmlns="urn:un:unece:uncefact:data:standard:CrossIndustryInvoice:100"
                                  xmlns:ram="urn:un:unece:uncefact:data:standard:ReusableAggregateBusinessInformationEntity:100"
                                  xmlns:udt="urn:un:unece:uncefact:data:standard:UnqualifiedDataType:100">
                <ExchangedDocument><ram:TypeCode>262</ram:TypeCode></ExchangedDocument>
                <SupplyChainTradeTransaction>
                    <ram:ApplicableHeaderTradeAgreement>
                        <ram:ContractReferencedDocument>
                            <ram:IssuerAssignedID>REBATE-2024</ram:IssuerAssignedID>
                        </ram:ContractReferencedDocument>
                    </ram:ApplicableHeaderTradeAgreement>
                    <ram:ApplicableHeaderTradeSettlement>
                        <ram:BillingSpecifiedPeriod>
                            <ram:StartDateTime>
                                <udt:DateTimeString format="102">20240101</udt:DateTimeString>
                            </ram:StartDateTime>
                            <ram:EndDateTime>
                                <udt:DateTimeString format="102">20241231</udt:DateTimeString>
                            </ram:EndDateTime>
                        </ram:BillingSpecifiedPeriod>
                    </ram:ApplicableHeaderTradeSettlement>
                </SupplyChainTradeTransaction>
            </CrossIndustryInvoice>
        ''')

        self.assertEqual(builder._get_import_document_amount_sign(tree), ('refund', 1))
        builder._import_fill_invoice_form(credit_note, tree, 1)

        self.assertRecordValues(credit_note, [{
            'x_studio_peppol_contract_document_reference_id': 'REBATE-2024',
            'x_studio_peppol_invoice_previous_date': False,
            'x_studio_peppol_invoice_period_start_date': fields.Date.to_date('2024-01-01'),
            'x_studio_peppol_invoice_period_end_date': fields.Date.to_date('2024-12-31'),
        }])


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestCreditNoteReferencesWithoutStudio(TestL10nFrPdpCommon):

    def test_export_without_studio_fields_reports_missing_reference(self):
        self.assertNotIn('x_studio_peppol_contract_document_reference_id', self.env['account.move']._fields)
        credit_note = self._create_french_invoice(move_type='out_refund')
        credit_note.action_post()

        _xml, errors = self.env['account.edi.xml.ubl_21_fr']._export_invoice(credit_note)

        self.assertTrue(any('x_studio_peppol_invoice_previous_date' in error for error in errors))
