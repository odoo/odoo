# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import fields
from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.exceptions import UserError
from odoo.tests import tagged
from odoo.tools.misc import file_open, file_path

from lxml import etree


@tagged('post_install', '-at_install')
class SDDTest(AccountTestInvoicingCommon):

    @classmethod
    def setUpClass(cls, chart_template_ref=None):
        super().setUpClass(chart_template_ref=chart_template_ref)
        cls.env.ref('base.EUR').active = True
        cls.env.user.email = "ruben.rybnik@sorcerersfortress.com"

    def create_account(self, number, partner, bank):
        return self.env['res.partner.bank'].create({
            'acc_number': number,
            'partner_id': partner.id,
            'bank_id': bank.id
        })

    def create_mandate(self,partner, partner_bank, one_off, company, payment_journal):
        return self.env['sdd.mandate'].create({
            'name': 'mandate ' + (partner.name or ''),
            'partner_bank_id': partner_bank.id,
            'one_off': one_off,
            'start_date': fields.Date.today(),
            'partner_id': partner.id,
            'company_id': company.id,
            'payment_journal_id': payment_journal.id
        })

    def create_invoice(self, partner):
        invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': partner.id,
            'currency_id': self.env.ref('base.EUR').id,
            'payment_reference': 'invoice to client',
            'invoice_line_ids': [(0, 0, {
                'product_id': self.env['product.product'].create({'name': 'A Test Product'}).id,
                'quantity': 1,
                'price_unit': 42,
                'name': 'something',
            })],
        })
        invoice.action_post()
        return invoice

    def pay_with_mandate(self, invoice, mandate):
        sdd_method_line = mandate.payment_journal_id.inbound_payment_method_line_ids.filtered(lambda l: l.code == 'sdd')
        self.env['account.payment.register'].with_context(active_model='account.move', active_ids=invoice.ids).create({
            'payment_date': invoice.invoice_date_due or invoice.invoice_date,
            'journal_id': mandate.payment_journal_id.id,
            'payment_method_line_id': sdd_method_line.id,
        })._create_payments()

    def test_sdd(self):
        country_belgium, country_china, country_germany = self.env['res.country'].search([('code', 'in', ['BE', 'CN', 'DE'])], limit=3, order='name ASC')

        # We setup our test company
        company = self.env.company
        company.country_id = country_belgium
        company.city = 'Company 1 City'
        company.sdd_creditor_identifier = 'BE30ZZZ300D000000042'
        company_bank_journal = self.company_data['default_journal_bank']
        company_bank_journal.bank_acc_number = 'CH9300762011623852957'
        bank_ing = self.env['res.bank'].create({'name': 'ING', 'bic': 'BBRUBEBB'})
        bank_bnp = self.env['res.bank'].create({'name': 'BNP Paribas', 'bic': 'GEBABEBB'})
        bank_no_bic = self.env['res.bank'].create({'name': 'NO BIC BANK'})
        company_bank_journal.bank_account_id.bank_id = bank_ing

        # Then we setup the banking data and mandates of two customers (one with a one-off mandate, the other with a recurrent one)
        partner_agrolait = self.env['res.partner'].create({'name': 'Agrolait', 'city': 'Agrolait Town', 'country_id': country_germany.id})
        partner_bank_agrolait = self.create_account('DE44500105175407324931', partner_agrolait, bank_ing)
        mandate_agrolait = self.create_mandate(partner_agrolait, partner_bank_agrolait, False, company, company_bank_journal)
        mandate_agrolait.action_validate_mandate()

        partner_china_export = self.env['res.partner'].create({'name': 'China Export', 'city': 'China Town'})
        partner_bank_china_export = self.create_account('SA0380000000608010167519', partner_china_export, bank_bnp)
        mandate_china_export = self.create_mandate(partner_china_export, partner_bank_china_export, True, company, company_bank_journal)
        mandate_china_export.action_validate_mandate()

        partner_no_bic = self.env['res.partner'].create({'name': 'NO BIC Co', 'city': 'NO BIC City', 'country_id': country_belgium.id})
        partner_bank_no_bic = self.create_account('BE68844010370034', partner_no_bic, bank_no_bic)
        mandate_no_bic = self.create_mandate(partner_no_bic, partner_bank_no_bic, True, company, company_bank_journal)
        mandate_no_bic.action_validate_mandate()

        # We create one invoice for each of our test customers ...
        invoice_agrolait = self.create_invoice(partner_agrolait)
        invoice_china_export = self.create_invoice(partner_china_export)
        invoice_no_bic = self.create_invoice(partner_no_bic)

        # Pay the invoices with mandates
        self.pay_with_mandate(invoice_agrolait, mandate_agrolait)
        self.pay_with_mandate(invoice_china_export, mandate_china_export)
        self.pay_with_mandate(invoice_no_bic, mandate_no_bic)

        # These invoice should have been paid thanks to the mandate
        self.assertEqual(invoice_agrolait.payment_state, self.env['account.move']._get_invoice_in_payment_state(), 'This invoice should have been paid thanks to the mandate')
        self.assertEqual(invoice_agrolait.sdd_mandate_id, mandate_agrolait)
        self.assertEqual(invoice_china_export.payment_state, self.env['account.move']._get_invoice_in_payment_state(), 'This invoice should have been paid thanks to the mandate')
        self.assertEqual(invoice_china_export.sdd_mandate_id, mandate_china_export)
        self.assertEqual(invoice_no_bic.payment_state, self.env['account.move']._get_invoice_in_payment_state(), 'This invoice should have been paid thanks to the mandate')
        self.assertEqual(invoice_no_bic.sdd_mandate_id, mandate_no_bic)

        #The 'one-off' mandate should now be closed
        self.assertEqual(mandate_agrolait.state, 'active', 'A recurrent mandate should stay confirmed after accepting a payment')
        self.assertEqual(mandate_china_export.state, 'closed', 'A one-off mandate should be closed after accepting a payment')
        self.assertEqual(mandate_no_bic.state, 'closed', 'A one-off mandate should be closed after accepting a payment')

        #Let us check the conformity of XML generation :
        # Test CORE PAIN 008.001.02
        company_bank_journal.debit_sepa_pain_version = 'pain.008.001.02'
        schema_file_path = file_path('account_sepa_direct_debit/schemas/pain.008.001.02.xsd')

        for invoice in (invoice_agrolait, invoice_china_export, invoice_no_bic):
            payment = invoice.line_ids.mapped('matched_credit_ids.credit_move_id.payment_id')
            xml_file = etree.fromstring(payment.generate_xml(company, fields.Date.today(), True))
            xml_schema = etree.XMLSchema(etree.parse(file_open(schema_file_path)))
            self.assertTrue(xml_schema.validate(xml_file), xml_schema.error_log.last_error)

        # Test CORE PAIN 008.001.08
        company_bank_journal.debit_sepa_pain_version = 'pain.008.001.08'
        schema_file_path = file_path('account_sepa_direct_debit/schemas/pain.008.001.08.xsd')

        for invoice in (invoice_agrolait, invoice_no_bic):
            payment = invoice.line_ids.mapped('matched_credit_ids.credit_move_id.payment_id')
            xml_file = etree.fromstring(payment.generate_xml(company, fields.Date.today(), True))
            xml_schema = etree.XMLSchema(etree.parse(file_open(schema_file_path)))
            self.assertTrue(xml_schema.validate(xml_file), xml_schema.error_log.last_error)

        payment = invoice_china_export.line_ids.mapped('matched_credit_ids.credit_move_id.payment_id')

        # Checks that an error is thrown if the country name or the city name is missing
        with self.assertRaises(UserError):
            xml_file = etree.fromstring(payment.generate_xml(company, fields.Date.today(), True))
        partner_china_export.write({'city': False, 'country_id': country_china})
        with self.assertRaises(UserError):
            xml_file = etree.fromstring(payment.generate_xml(company, fields.Date.today(), True))

        # Checks that the xml is correctly generated when both the city_name and country are set
        partner_china_export.write({'city': 'China Town', 'country_id': country_china})
        xml_file = etree.fromstring(payment.generate_xml(company, fields.Date.today(), True))
        xml_schema = etree.XMLSchema(etree.parse(file_open(schema_file_path)))
        self.assertTrue(xml_schema.validate(xml_file), xml_schema.error_log.last_error)

        # Test B2B sdd scheme
        company_bank_journal.debit_sepa_pain_version = 'pain.008.001.02'
        schema_file_path = file_path('account_sepa_direct_debit/schemas/EPC131-08_2019_V1.0_pain.008.001.02.xsd')
        mandate_agrolait.sdd_scheme = 'B2B'
        mandate_china_export.sdd_scheme = 'B2B'
        mandate_no_bic.sdd_scheme = 'B2B'

        for invoice in (invoice_agrolait, invoice_china_export, invoice_no_bic):
            payment = invoice.line_ids.mapped('matched_credit_ids.credit_move_id.payment_id')
            xml_file = etree.fromstring(payment.generate_xml(company, fields.Date.today(), True))
            xml_schema = etree.XMLSchema(etree.parse(file_open(schema_file_path)))
            self.assertTrue(xml_schema.validate(xml_file), xml_schema.error_log.last_error)
