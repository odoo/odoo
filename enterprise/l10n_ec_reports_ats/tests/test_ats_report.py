# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from freezegun import freeze_time
from datetime import timedelta

from odoo import Command, fields, tools
from odoo.tests import tagged
from odoo.addons.l10n_ec_edi.tests.test_edi_xml import TestEcEdiCommon
from odoo.addons.account_reports.tests.common import TestAccountReportsCommon

@tagged('ats_tests_l10n', 'post_install_l10n', 'post_install', '-at_install')
class TestAtsReport(TestEcEdiCommon, TestAccountReportsCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # For ATS report, the partner company must be have RUC identification type
        cls.company_data['company'].partner_id.write({'l10n_latam_identification_type_id': cls.env.ref('l10n_ec.ec_ruc').id})

        # Partners
        cls.partner_ced = cls.env['res.partner'].create({
            'name': 'cliente_ced',
            'is_company': False,
            'street': 'Av. 10 de Agosto',
            'country_id': cls.env.ref('base.ec').id,
            'l10n_latam_identification_type_id': cls.env.ref('l10n_ec.ec_dni').id,
            'vat': '0704396241'
        })
        cls.partner_ruc = cls.env['res.partner'].create({
            'name': 'cliente_ruc',
            'is_company': True,
            'street': 'Av. Carlos Mejia',
            'country_id': cls.env.ref('base.ec').id,
            'l10n_latam_identification_type_id': cls.env.ref('l10n_ec.ec_ruc').id,
            'vat': '1768156470001'
        })
        cls.partner_ext = cls.env['res.partner'].create({
            'name': 'cliente_ext',
            'is_company': False,
            'street': 'Stone Street',
            'country_id': cls.env.ref('base.us').id,
            'l10n_latam_identification_type_id': cls.env.ref('l10n_latam_base.it_fid').id,
            'vat': '1234567890'
        })
        cls.partner_pas = cls.env['res.partner'].create({
            'name': 'cliente_pas',
            'is_company': False,
            'street': 'Calle Durán',
            'country_id': cls.env.ref('base.ec').id,
            'l10n_latam_identification_type_id': cls.env.ref('l10n_latam_base.it_pass').id,
            'vat': '0701733727'
        })

        # Journals
        cls.journal_inv_one = cls.env['account.journal'].search([
            ('company_id', '=', cls.company_data['company'].id),
            ('code', '=', 'INV')
        ])
        cls.journal_inv_two = cls.env['account.journal'].create({
            'name': '001-002 Facturas de cliente',
            'type': 'sale',
            'l10n_ec_entity': '001',
            'l10n_ec_emission': '002',
            'l10n_ec_emission_address_id': cls.company_data['company'].partner_id.id,
            'default_account_id': cls.env['account.account'].search([('code', '=', '410201')], limit=1).id,
            'l10n_latam_use_documents': True,
            'refund_sequence': True,
            'code': 'INV2',
        })
        cls.journal_inv_three = cls.env['account.journal'].create({
            'name': '001-003 Facturas de cliente',
            'type': 'sale',
            'l10n_ec_entity': '001',
            'l10n_ec_emission': '003',
            'l10n_ec_emission_address_id': cls.company_data['company'].partner_id.id,
            'default_account_id': cls.env['account.account'].search([('code', '=', '410201')], limit=1).id,
            'l10n_latam_use_documents': True,
            'refund_sequence': True,
            'edi_format_ids': [Command.unlink(cls.env.ref('l10n_ec_edi.ecuadorian_edi_format').id)],
            'code': 'INV3',
        })
        cls.journal_purchase = cls.env['account.journal'].search([
            ('company_id', '=', cls.company_data['company'].id),
            ('code', '=', 'BILL')]
        )
        cls.journal_liquidation = cls.env['account.journal'].search([
            ('company_id', '=', cls.company_data['company'].id),
            ('code', '=', 'LIQCO')]
        )

        # Products
        cls.product_service = cls.env['product.product'].create({
            'name': 'Servicio de Mantenimiento',
            'type': 'service',
            'list_price': 100.0,
            'default_code': 'SOOO1',
            'barcode': '123456789'
        })

        # EC payment method
        cls.sri_payment_id = cls.env['l10n_ec.sri.payment'].search([('code', '=', '01')], limit=1).id


    # ============== TESTS ==============

    def test_ats_sale(self):
        """ Test the ATS report with sale invoices, credit notes and debit notes. """
        with freeze_time(self.frozen_today):
            ## Step 1: test with just invoices
            invoices = self._generate_sale_invoices()
            xml_content_ats = self._get_ats_xml_content()
            self.assert_xml_ats_equal(xml_content_ats, 'ats_sale_invoices.xml')

            ## Step 2: test with credit notes as well
            credit_notes = self._create_credit_notes(invoices[0:6])
            credit_notes.action_post()
            xml_content_ats = self._get_ats_xml_content()
            self.assert_xml_ats_equal(xml_content_ats, 'ats_sale_returns.xml')

            ## Step 3: test with debit notes as well
            # Create an invoice for a physical emission point
            physical_invoice = self._generate_sale_physical_invoice()

            # Create debit notes for invoices 1 (RUC), 2 (cedula), 4 (passport), and the physical invoice
            self._create_debit_notes(invoices[0:2] | invoices[3] | physical_invoice)

            xml_content_ats = self._get_ats_xml_content()
            self.assert_xml_ats_equal(xml_content_ats, 'ats_sale_debit_notes.xml')

    def test_ats_purchase(self):
        """ Test the ATS report with purchase invoices and a credit note. """
        with freeze_time(self.frozen_today):
            ## Step 1: test with just purchase invoices
            invoices = self._generate_purchase_invoices()
            xml_content_ats = self._get_ats_xml_content()
            self.assert_xml_ats_equal(xml_content_ats, 'ats_purchase_invoices.xml')

            ## Step 2: test with a credit note for invoice 8
            credit_note = self._create_credit_notes(invoices[7])
            credit_note.write({
                'l10n_latam_document_number': '001-001-000000099',
            })
            credit_note.action_post()

            xml_content_ats = self._get_ats_xml_content()
            self.assert_xml_ats_equal(xml_content_ats, 'ats_purchase_returns.xml')

    def test_ats_cancelled(self):
        """ Test the ATS report with cancelled invoices and credit notes. """
        with freeze_time(self.frozen_today):
            # Cancelled sale invoice and credit note
            invoices = self._generate_cancelled_sale_invoices()
            credit_note = self._create_credit_notes(invoices[1])
            credit_note.action_post()
            credit_note.button_cancel()

            # Cancelled purchase liquidation
            self._generate_cancelled_purchase_liquidation()
            # Non-cancelled purchase invoice. This should not appear with the cancelled docs.
            self._generate_non_cancelled_purchase_invoice()

            # Cancelled draft invoice should not appear in the report
            draft_invoice = self.env['account.move'].create({
                'move_type': 'out_invoice',
                'l10n_ec_sri_payment_id': self.sri_payment_id,
                'partner_id': self.partner_ruc.id,
                'journal_id': self.journal_inv_one.id,
                'invoice_line_ids': [self._get_invoice_line_with_price_vals(price_unit=100)],
            })
            draft_invoice.button_cancel()

            xml_content_ats = self._get_ats_xml_content()
            self.assert_xml_ats_equal(xml_content_ats, 'ats_cancelled.xml')

    def test_ats_reimbursement(self):
        """ Test the ATS report with reimbursements """
        with freeze_time(self.frozen_today):
            self._generate_purchase_reimbursements()
            xml_content_ats = self._get_ats_xml_content()
            self.assert_xml_ats_equal(xml_content_ats, 'ats_purchase_reimbursements.xml')

    # ============== HELPERS: SALE ==============

    def _generate_sale_invoices(self):
        invoices_vals = [
            {
                'l10n_latam_document_number': '001-001-000000001',
                'partner_id': self.partner_ruc.id,
                'journal_id': self.journal_inv_one.id,
                'invoice_line_ids': [self._get_invoice_line_with_price_vals(price_unit=101)],
            },
            {
                'l10n_latam_document_number': '001-002-000000001',
                'partner_id': self.partner_ced.id,
                'journal_id': self.journal_inv_two.id,
                'invoice_line_ids': [self._get_invoice_line_with_price_vals(price_unit=102)],
            },
            {
                'l10n_latam_document_number': '001-001-000000002',
                'partner_id': self.partner_ruc.id,
                'journal_id': self.journal_inv_one.id,
                'invoice_line_ids': [self._get_invoice_line_with_price_vals(price_unit=103)],
            },
            {
                'l10n_latam_document_number': '001-002-000000002',
                'partner_id': self.partner_pas.id,
                'journal_id': self.journal_inv_two.id,
                'invoice_line_ids': [self._get_invoice_line_with_price_vals(price_unit=104)],
            },
            {
                'l10n_latam_document_number': '001-001-000000003',
                'partner_id': self.partner_ext.id,
                'journal_id': self.journal_inv_one.id,
                'invoice_line_ids': [self._get_invoice_line_with_price_vals(price_unit=105)],
            },
            {
                'l10n_latam_document_number': '001-001-000000004',
                'partner_id': self.partner_ruc.id,
                'journal_id': self.journal_inv_one.id,
                'invoice_line_ids': [self._get_invoice_line_with_price_vals(price_unit=106)],
            },
            {
                'l10n_latam_document_number': '001-001-000000005',
                'partner_id': self.partner_ced.id,
                'journal_id': self.journal_inv_one.id,
                'invoice_line_ids': [self._get_invoice_line_with_price_vals(price_unit=108)],
            },
            {
                'l10n_latam_document_number': '001-001-000000006',
                'partner_id': self.partner_ruc.id,
                'journal_id': self.journal_inv_one.id,
                'invoice_line_ids': [self._get_invoice_line_with_price_vals(price_unit=107)],
            },
        ]

        for i, invoice_vals in enumerate(invoices_vals):

            invoice_vals.update({
                'move_type': 'out_invoice',
                'l10n_ec_sri_payment_id': self.sri_payment_id,
                'invoice_date': self.frozen_today.replace(day=1) + timedelta(days=i),
            })

        invoices = self.env['account.move'].create(invoices_vals)

        # Invoices 1-6 will be posted. Invoice 7 will be cancelled. Invoice 8 will stay as draft.
        invoices[0:7].action_post()

        # Create withhold for invoices to partners using RUC
        self._create_withhold(
            invoices[0],
            withhold_sequence=1,
            withhold_lines=[
                Command.create({'tax_id': self._get_tax_by_xml_id('tax_withhold_vat_10').id}),
                Command.create({'tax_id': self._get_tax_by_xml_id('tax_withhold_profit_sale_1_75x100').id})
            ]
        )
        self._create_withhold(
            invoices[2],
            withhold_sequence=2,
            withhold_lines=[
                Command.create({'tax_id': self._get_tax_by_xml_id('tax_withhold_vat_10').id}),
                Command.create({'tax_id': self._get_tax_by_xml_id('tax_withhold_profit_sale_1_75x100').id})
            ]
        )
        self._create_withhold(
            invoices[5],
            withhold_sequence=3,
            withhold_lines=[
                Command.create({'tax_id': self._get_tax_by_xml_id('tax_withhold_vat_20').id}),
                Command.create({'tax_id': self._get_tax_by_xml_id('tax_withhold_profit_sale_2x100').id})
            ]
        )

        # Cancel invoice 7
        invoices[6].button_cancel()

        return invoices

    def _generate_sale_physical_invoice(self):
        ''' Create an invoice with a physical emission point '''
        physical_invoice_vals = [{
            'move_type': 'out_invoice',
            'l10n_ec_sri_payment_id': self.sri_payment_id,
            'l10n_latam_document_number': '001-003-000000001',
            'l10n_ec_authorization_number': '1234567890',  # physical invoice has 10-digit authorization number
            'partner_id': self.partner_ruc.id,
            'journal_id': self.journal_inv_three.id,
            'invoice_line_ids': [self._get_invoice_line_with_price_vals(price_unit=110)],
        }]
        physical_invoice = self.env['account.move'].create(physical_invoice_vals)
        physical_invoice.action_post()
        self._create_withhold(
            physical_invoice,
            withhold_sequence=1,
            withhold_lines=[
                    Command.create({'tax_id': self._get_tax_by_xml_id('tax_withhold_vat_10').id}),
                    Command.create({'tax_id': self._get_tax_by_xml_id('tax_withhold_profit_sale_1_75x100').id})
            ]
        )
        return physical_invoice

    # ============== HELPERS: PURCHASE ==============

    def _generate_purchase_invoices(self):
        def get_invoice_line_vals(lines_number=4):
            lines = []
            tax_list = {
                4: ['tax_vat_510_sup_01', 'tax_vat_517_sup_07', 'tax_vat_541_sup_02', 'tax_vat_542_sup_02'],
                3: ['tax_vat_542_sup_02', 'tax_vat_541_sup_02', 'tax_vat_542_sup_02'],
                32: ['tax_vat_510_sup_01', 'tax_vat_541_sup_02', 'tax_vat_542_sup_02'],
                33: ['tax_vat_517_sup_07', 'tax_vat_541_sup_02', 'tax_vat_542_sup_02'],
                1: ['tax_vat_541_sup_02'],
            }
            for tax in tax_list.get(lines_number, []):
                lines.append(self._get_invoice_line_with_price_vals(tax_xml_id=tax, price_unit=10.00))
            if lines_number == 0:
                lines.append(self._get_invoice_line_with_price_vals(tax_xml_id=False, price_unit=10.00))
            return lines

        invoices_to_create = {
            self.partner_ced: [
                ('03', '01', 4),
                ('19', '01', 1),
            ],
            self.partner_ext: [
                ('03', '01', 4),
                ('15', '01', 0),
                ('19', '01', 1),
            ],
            self.partner_pas: [
                ('03', '16', 4),
                ('19', '19', 1),
            ],
            self.partner_ruc: [
                ('01', '01', 4),
                ('02', '01', 33),
                ('11', '01', 32),
                ('12', '19', 32),
                ('19', '19', 1),
                ('20', '20', 3),
                ('21', '20', 32),
            ],
        }

        invoices_vals = []
        num_invoice = 1
        for partner, invoices_data in invoices_to_create.items():
            for document_code, payment_code, lines_number in invoices_data:
                journal = self.journal_liquidation if document_code == '03' else self.journal_purchase
                invoice_vals = {
                    'move_type': 'in_invoice',
                    'invoice_date': self.frozen_today.replace(day=1) + timedelta(days=num_invoice),
                    'partner_id': partner.id,
                    'journal_id': journal.id,
                    'l10n_latam_document_type_id': self.env.ref(f'l10n_ec.ec_dt_{document_code}').id,
                    'invoice_line_ids': get_invoice_line_vals(lines_number),
                    'l10n_ec_sri_payment_id': self.env['l10n_ec.sri.payment'].search([('code', '=', payment_code)], limit=1).id,
                    'l10n_latam_document_number': num_invoice,
                }
                if journal.company_id.account_fiscal_country_id.code == 'EC' and document_code in ['01', '02', '03']:
                    invoice_vals.update({'l10n_latam_document_number': f'001-001-{num_invoice:09}'})

                invoices_vals.append(invoice_vals)
                num_invoice += 1

        invoices = self.env['account.move'].create(invoices_vals)

        invoices.action_post()

        self._create_withhold(
            invoices[0],
            withhold_sequence=1,
            withhold_lines=[
                Command.clear(),
                Command.create({'tax_id': self._get_tax_by_xml_id('tax_withhold_profit_311').id, 'taxsupport_code': '01', 'base': 10.00, 'amount': 0.20}),
                Command.create({'tax_id': self._get_tax_by_xml_id('tax_withhold_profit_311').id, 'taxsupport_code': '07', 'base': 10.00, 'amount': 0.20}),
                Command.create({'tax_id': self._get_tax_by_xml_id('tax_withhold_profit_311').id, 'taxsupport_code': '02', 'base': 20.00, 'amount': 0.40}),
                Command.create({'tax_id': self._get_tax_by_xml_id('tax_withhold_vat_100').id, 'taxsupport_code': '01', 'amount': 1.20, 'base': 1.20}),
            ],
        )
        self._create_withhold(invoices[2], withhold_sequence=2)
        self._create_withhold(invoices[5], withhold_sequence=3)
        self._create_withhold(
            invoices[7],
            withhold_sequence=4,
            withhold_lines=[
                Command.clear(),
                Command.create({'tax_id': self._get_tax_by_xml_id('tax_withhold_profit_312').id, 'taxsupport_code': '01', 'base': 10.00, 'amount': 0.18}),
                Command.create({'tax_id': self._get_tax_by_xml_id('tax_withhold_profit_312').id, 'taxsupport_code': '07', 'base': 10.00, 'amount': 0.18}),
                Command.create({'tax_id': self._get_tax_by_xml_id('tax_withhold_profit_312').id, 'taxsupport_code': '02', 'base': 20.00, 'amount': 0.35}),
            ],
        )
        self._create_withhold(
            invoices[8],
            withhold_sequence=5,
            withhold_lines=[
                Command.clear(),
                Command.create({'tax_id': self._get_tax_by_xml_id('tax_withhold_profit_312').id, 'taxsupport_code': '07', 'base': 10.00, 'amount': 0.18}),
                Command.create({'tax_id': self._get_tax_by_xml_id('tax_withhold_profit_312').id, 'taxsupport_code': '02', 'base': 20.00, 'amount': 0.35}),
            ],
        )
        self._create_withhold(
            invoices[9],
            withhold_sequence=6,
            withhold_lines=[
                Command.clear(),
                Command.create({'tax_id': self._get_tax_by_xml_id('tax_withhold_profit_312').id, 'taxsupport_code': '01', 'base': 10.00, 'amount': 0.18}),
                Command.create({'tax_id': self._get_tax_by_xml_id('tax_withhold_profit_312').id, 'taxsupport_code': '02', 'base': 20.00, 'amount': 0.35}),
            ]
        )
        self._create_withhold(invoices[10], withhold_sequence=7)
        self._create_withhold(invoices[12], withhold_sequence=8)

        return invoices

    # ============== HELPERS: CANCELLED ==============

    def _generate_cancelled_sale_invoices(self):
        invoices_vals = [
            {
                'move_type': 'out_invoice',
                'l10n_ec_sri_payment_id': self.sri_payment_id,
                'l10n_latam_document_number': '001-001-000000006',
                'partner_id': self.partner_ruc.id,
                'journal_id': self.journal_inv_one.id,
                'invoice_line_ids': [self._get_invoice_line_with_price_vals(price_unit=100)]
            },
            {
                'move_type': 'out_invoice',
                'l10n_ec_sri_payment_id': self.sri_payment_id,
                'l10n_latam_document_number': '001-001-000000007',
                'partner_id': self.partner_ced.id,
                'journal_id': self.journal_inv_one.id,
                'invoice_line_ids': [self._get_invoice_line_with_price_vals(price_unit=99)]
            },
        ]
        invoices = self.env['account.move'].create(invoices_vals)
        invoices.action_post()
        invoices[0].button_cancel()

        return invoices

    def _generate_cancelled_purchase_liquidation(self):
        # Creation of cancel purchase liquidation

        purchase_liquidation = self.get_invoice({
            'move_type': 'in_invoice',
            'partner_id': self.partner_ruc.id,
            'journal_id': self.journal_liquidation.id,
            'invoice_line_ids': [self._get_invoice_line_with_price_vals(tax_xml_id='tax_vat_510_sup_01', price_unit=60.00)]
        })
        purchase_liquidation.action_post()
        purchase_liquidation.button_cancel()

    def _generate_non_cancelled_purchase_invoice(self):
        invoice_vals = [
            {
                'move_type': 'in_invoice',
                'l10n_ec_sri_payment_id': self.sri_payment_id,
                'l10n_latam_document_number': '001-001-000000009',
                'partner_id': self.partner_ruc.id,
                'journal_id': self.journal_purchase.id,
                'l10n_latam_document_type_id': self.env.ref('l10n_ec.ec_dt_01').id,
                'invoice_line_ids': [self._get_invoice_line_with_price_vals(tax_xml_id='tax_vat_510_sup_01', price_unit=10.00)],
                'invoice_date': self.frozen_today,
            }
        ]

        invoice = self.env['account.move'].create(invoice_vals)
        invoice.action_post()
        # Create a purchase withhold
        self._create_withhold(
            invoice,
            withhold_sequence=1,
        )
        # Cancel the created withhold
        withhold = self.env['account.move.line'].search([('l10n_ec_withhold_invoice_id', '=', invoice.id)]).move_id
        withhold.button_cancel()
        return invoice

    def _get_reimbursement_line_vals(self, invoice, lines, tax_base=10.0):
        """ Add reimbursement line on the invoice """
        reimbursement_lines = []
        for i, tax_xml_id in enumerate(lines):
            reimbursement_lines.append(Command.create({
                'authorization_number': '1234567890',
                'partner_id': self.partner_ruc.id,
                'l10n_latam_document_type_id': self.env.ref('l10n_ec.ec_dt_01').id,
                'document_number': f'001-001-{i + 1:09}',
                'date': invoice.invoice_date,
                'tax_id': self._get_tax_by_xml_id(tax_xml_id).id,
                'tax_base': tax_base,
                'partner_vat_number': self.partner_ruc.vat,
                'partner_vat_type_id': self.partner_ruc.l10n_latam_identification_type_id.id,
                'partner_country_id': self.partner_ruc.country_id.id,
            }))
        invoice.write({'l10n_ec_reimbursement_ids': reimbursement_lines})

    def _generate_purchase_reimbursements(self):
        def get_tax_xml_id(sup_number=4):
            tax_list = {
                4: ['tax_vat_510_sup_01', 'tax_vat_510_sup_01', 'tax_vat_510_sup_01', 'tax_vat_510_sup_01'],
                3: ['tax_vat_542_sup_02', 'tax_vat_541_sup_02', 'tax_vat_542_sup_02'],
                1: ['tax_vat_541_sup_02'],
            }
            return tax_list.get(sup_number, [])

        invoices_to_create = {
            self.partner_ced: [
                ('03', '01', 3),
            ],
            self.partner_ruc: [
                ('01', '01', 4),
                ('01', '01', 3),
                ('01', '01', 1),
            ],
        }

        num_invoice = 1
        self.journal_liquidation.default_account_id = self.company_data['default_account_assets']
        for partner, invoices_data in invoices_to_create.items():
            for document_code, payment_code, lines_number in invoices_data:
                journal = self.journal_liquidation if document_code == '03' else self.journal_purchase
                invoice_vals = {
                    'move_type': 'in_invoice',
                    'invoice_date': self.frozen_today.replace(day=1) + timedelta(days=num_invoice),
                    'partner_id': partner.id,
                    'journal_id': journal.id,
                    'l10n_latam_document_type_id': self.env.ref(f'l10n_ec.ec_dt_{document_code}').id,
                    'l10n_ec_sri_payment_id': self.env['l10n_ec.sri.payment'].search([('code', '=', payment_code)], limit=1).id,
                    'l10n_latam_document_number': num_invoice,
                }
                if journal.company_id.account_fiscal_country_id.code == 'EC' and document_code in ['01', '02', '03']:
                    invoice_vals.update({'l10n_latam_document_number': f'001-001-{num_invoice:09}'})

                in_invoice = self.env['account.move'].create(invoice_vals)
                self._get_reimbursement_line_vals(invoice=in_invoice, lines=get_tax_xml_id(lines_number))
                in_invoice.l10n_ec_action_compute_lines_from_reimbursements()  # Compute invoice lines from reimbursements
                in_invoice.action_post()
                num_invoice += 1

    # ============== COMMON HELPERS ==============

    def _get_invoice_line_with_price_vals(self, tax_xml_id='tax_vat_411_goods', **kwargs):
        # Return invoice product lines
        vals = {
            'product_id': self.product_service.id,
            'quantity': 1,
            'discount': 0,
            'tax_ids': [Command.set(self._get_tax_by_xml_id(tax_xml_id).ids)] if tax_xml_id else False,
        }
        if kwargs:
            vals.update(kwargs)
        return Command.create(vals)

    def _create_withhold(self, invoice, withhold_sequence, withhold_lines=None):
        entity = invoice.journal_id.l10n_ec_entity
        emission = invoice.journal_id.l10n_ec_emission
        wizard = self.env['l10n_ec.wizard.account.withhold'].with_context(active_ids=invoice.ids, active_model='account.move').create({})
        wizard.document_number = f'{entity.zfill(3)}-{emission.zfill(3)}-{withhold_sequence:09}'
        if withhold_lines:
            wizard.write({
                'withhold_line_ids': withhold_lines
            })
        if wizard.partner_country_code != 'EC':
            wizard.foreign_regime = '01'
        wizard.action_create_and_post_withhold()
        # Hacky, but necessary, because the wizard doesn't trigger the dependencies of this compute...
        invoice._compute_l10n_ec_withhold_inv_fields()

    def _create_credit_notes(self, invoices):
        reverse_moves = self.env['account.move']
        for invoice in invoices:
            wizard_vals = {'journal_id': invoice.journal_id.id}
            wizard_reverse = self.env['account.move.reversal'].with_context(active_ids=invoice.ids, active_model='account.move').create(wizard_vals)
            # create credit note and get dictionary result
            reverse_moves_dict = wizard_reverse.reverse_moves()
            reverse_move = self.env['account.move'].browse(reverse_moves_dict.get('res_id', False))
            for invoice_line in reverse_move.invoice_line_ids:
                invoice_line.price_unit = invoice_line.price_unit / 2
            reverse_moves |= reverse_move
        return reverse_moves

    def _create_debit_notes(self, invoices):
        for invoice in invoices:
            debit_note_wizard = self.env['account.debit.note'].with_context(active_model="account.move", active_ids=invoice.ids).create({
                'date': self.frozen_today,
                'reason': 'no reason',
                'copy_lines': True,
                'journal_id': invoice.journal_id.id,
            })
            action = debit_note_wizard.create_debit()
            debit_note = self.env['account.move'].browse(action['res_id'])
            debit_note.action_post()

    def _get_ats_xml_content(self):
        # Generate xml content of ats
        report = self.env.ref('l10n_ec.tax_report_104')
        options = self._generate_options(report, fields.Date.to_date('2022-01-01'), fields.Date.to_date('2023-01-01'))
        set_time_interval_function = self.env[report._get_custom_handler_model()].l10n_ec_export_ats
        xml_content_ats = set_time_interval_function(options)
        return xml_content_ats['file_content']

    def assert_xml_ats_equal(self, generated_xml, expected_xml_filename):
        # Verify the expected xml against the generated xml
        with tools.file_open(f'l10n_ec_reports_ats/tests/expected_xmls/{expected_xml_filename}', 'rb') as expected_xml_file:
            self.assertXmlTreeEqual(
                self.get_xml_tree_from_string(generated_xml.encode()),
                self.get_xml_tree_from_string(expected_xml_file.read())
            )
