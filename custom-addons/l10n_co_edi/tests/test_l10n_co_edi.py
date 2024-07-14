# coding: utf-8
from odoo import Command
from .common import TestCoEdiCommon
from odoo.tests import tagged
from odoo.tools import mute_logger, misc

@tagged('post_install_l10n', 'post_install', '-at_install')
class TestColombianInvoice(TestCoEdiCommon):

    def l10n_co_assert_generated_file_equal(self, invoice, expected_values, applied_xpath=None):
        # Get the file that we generate instead of the response from carvajal
        invoice.action_post()
        xml_content = self.edi_format._l10n_co_edi_generate_xml(invoice)
        current_etree = self.get_xml_tree_from_string(xml_content)
        expected_etree = self.get_xml_tree_from_string(expected_values)
        if applied_xpath:
            expected_etree = self.with_applied_xpath(expected_etree, applied_xpath)
        self.assertXmlTreeEqual(current_etree, expected_etree)

    def test_invoice(self):
        '''Tests if we generate an accepted XML for an invoice and a credit note.'''
        with self.mock_carvajal():
            self.l10n_co_assert_generated_file_equal(self.invoice, self.expected_invoice_xml)

            # To stop a warning about "Tax Base Amount not computable
            # probably due to a change in an underlying tax " which seems
            # to be expected when generating refunds.
            with mute_logger('odoo.addons.account.models.account_invoice'):
                credit_note = self.invoice._reverse_moves(default_values_list=[{'l10n_co_edi_description_code_credit': '1'}])

            self.l10n_co_assert_generated_file_equal(credit_note, self.expected_credit_note_xml)

    def test_invoice_multicurrency(self):
        '''Tests if we generate an accepted XML for an invoice in non-company currency
           Note for this test it is important that we use 'round_globally' and not 'round_per_line'
           For 'round_per_line' there are issues with the validation of the taxes. The generated XML will not be accepted.
           The problem with 'round_per_line' is that we round the tax in document currency and then convert the rounded amount to company currency.
           The rounding error (fine in document currency) can become a problem after the conversion to company currency if the conversion rate is big enough:
           For example:
              * both currencies rounded to 0.01
              * currency rate: 3919.109578
              * tax rate: 15 %
                tag: IMP_6
              * odoo base amount in document currency: 226.98
              * odoo tax  amount in document currency: 34.05 = round(0.15 * 226.98, 2)
              * "effective tax rate": 15.00132170235263 %
              * odoo base amount in company  currency: 889559.49
                tag: IMP_2
              * odoo tax  amount in company  currency: 133445.68 = round(34.05 * 3919.109578, 2)
                tag: IMP_4
              * BUT: 0.15 * 889559.49 = 133433.92
                so we are off by ≈ 11.76 in company currency tax
           This fails the validation: tax_rate * base_amount == tax_amount
                                      (in tags: IMP_6 * IMP_2 == IMP_4)
        '''
        with self.mock_carvajal():
            self.l10n_co_assert_generated_file_equal(self.invoice_multicurrency, self.expected_invoice_multicurrency_xml)

    def test_sugar_tax_invoice(self):
        ''' Tests if we generate an accepted XML for an invoice with products
            that have sugar tax applied.
        '''
        with self.mock_carvajal():
            self.l10n_co_assert_generated_file_equal(self.sugar_tax_invoice, self.expected_sugar_tax_invoice_xml)

    def test_invoice_tim_sections(self):
        ''' Tests the grouping of taxes inside the TIM section. There should be one TIM per CO tax type, and inside
        this TIM, one IMP per tax rate.
        '''
        with self.mock_carvajal():
            self.l10n_co_assert_generated_file_equal(self.invoice_tim, self.expected_invoice_tim_xml)

    def test_invoice_with_attachment_url(self):
        with self.mock_carvajal():
            self.invoice.l10n_co_edi_attachment_url = 'http://testing.te/test.zip'
            applied_xpath = '''
                <xpath expr="//ENC_16" position="after">
                    <ENC_17>http://testing.te/test.zip</ENC_17>
                </xpath>
            '''
            self.l10n_co_assert_generated_file_equal(self.invoice, self.expected_invoice_xml, applied_xpath)

    def test_invoice_carvajal_group_of_taxes(self):
        with self.mock_carvajal():
            self.invoice.write({
                'invoice_line_ids': [(1, self.invoice.invoice_line_ids.id, {
                    'tax_ids': [(6, 0, self.tax_group.ids)],
                    'name': 'Line 1',  # Otherwise it is recomputed
                })],
            })
            self.l10n_co_assert_generated_file_equal(self.invoice, self.expected_invoice_xml)

    def test_setup_tax_type(self):
        for xml_id, expected_type in [
            ("account.l10n_co_tax_4", "l10n_co_edi.tax_type_0"),
            ("account.l10n_co_tax_8", "l10n_co_edi.tax_type_0"),
            ("account.l10n_co_tax_9", "l10n_co_edi.tax_type_0"),
            ("account.l10n_co_tax_10", "l10n_co_edi.tax_type_0"),
            ("account.l10n_co_tax_11", "l10n_co_edi.tax_type_0"),
            ("account.l10n_co_tax_53", "l10n_co_edi.tax_type_5"),
            ("account.l10n_co_tax_54", "l10n_co_edi.tax_type_5"),
            ("account.l10n_co_tax_55", "l10n_co_edi.tax_type_4"),
            ("account.l10n_co_tax_56", "l10n_co_edi.tax_type_4"),
            ("account.l10n_co_tax_57", "l10n_co_edi.tax_type_6"),
            ("account.l10n_co_tax_58", "l10n_co_edi.tax_type_6"),
            ("account.l10n_co_tax_covered_goods", "l10n_co_edi.tax_type_0")
        ]:
            tax = self.env.ref(xml_id, raise_if_not_found=False)
            if tax:
                self.assertEqual(tax.l10n_co_edi_type, expected_type)

    def test_debit_note_creation_wizard(self):
        """ Test debit note is create succesfully """

        self.invoice.action_post()

        wizard = self.env['account.debit.note'].with_context(active_model="account.move", active_ids=self.invoice.ids).create({
            'l10n_co_edi_description_code_debit': '1',
            'copy_lines': True,
        })
        wizard.create_debit()

        debit_note = self.env['account.move'].search([
            ('debit_origin_id', '=', self.invoice.id),
        ])
        self.assertRecordValues(debit_note, [{'amount_total': 43875.0}])

    def test_invoice_withholded_taxes(self):
        company = self.company_data['company']

        withholded_15_on_19 = self.env.ref(f'account.{company.id}_l10n_co_tax_56')
        withholded_15_on_5 = self.env.ref(f'account.{company.id}_l10n_co_tax_55')

        invoice = self.env['account.move'].create({
            'partner_id': company.partner_id.id,
            'move_type': 'out_invoice',
            'ref': 'reference',
            'invoice_payment_term_id': self.env.ref('account.account_payment_term_end_following_month').id,
            'invoice_line_ids': [
                Command.create({
                    'quantity': 1,
                    'price_unit': 100.9,
                    'name': 'Line 1',
                    'tax_ids': [Command.set(withholded_15_on_19.ids)],
                }),
                Command.create({
                    'quantity': 1,
                    'price_unit': 101,
                    'name': 'Line 2',
                    'tax_ids': [Command.set(withholded_15_on_5.ids)],
                }),
            ]
        })

        expected_invoice_taxes_withholded = misc.file_open('l10n_co_edi/tests/invoice_taxes_withholded.xml', 'rb').read()

        with self.mock_carvajal():
            self.l10n_co_assert_generated_file_equal(invoice, expected_invoice_taxes_withholded)

    def test_vendor_bill(self):
        with self.mock_carvajal():
            self.l10n_co_assert_generated_file_equal(self.in_invoice, self.expected_in_invoice_xml)

    def test_debit_note_out_invoice(self):
        '''Tests generation of a debit note from a credit note.'''
        with self.mock_carvajal():
            credit_note = self.invoice._reverse_moves(default_values_list=[{'l10n_co_edi_description_code_credit': '1'}])
            credit_note.action_post()
            move_debit_note_wiz = self.env['account.debit.note'].with_context(
                active_model="account.move",
                active_ids=credit_note.ids
            ).create({
                'date': self.frozen_today,
                'reason': 'no reason',
                'l10n_co_edi_description_code_debit': '4',
            })
            res = move_debit_note_wiz.create_debit()
            debit_note = self.env['account.move'].browse(res.get('res_id'))

            # Check the generated debit note has lines
            self.assertTrue(debit_note.line_ids)

            expected_debit_note_xml = misc.file_open('l10n_co_edi/tests/accepted_debit_note.xml', 'rb').read()
            self.l10n_co_assert_generated_file_equal(debit_note, expected_debit_note_xml)

    def test_debit_note_in_refund(self):
        '''Tests generation of a debit note from a vendor refund.'''
        with self.mock_carvajal():
            bill = self.init_invoice('in_invoice', products=self.product_a)
            bill.partner_id = self.company_data['company'].partner_id
            bill.action_post()
            credit_note = bill._reverse_moves(default_values_list=[{
                'l10n_co_edi_description_code_credit': '1',
                'invoice_date': self.frozen_today,
            }])
            credit_note.action_post()
            move_debit_note_wiz = self.env['account.debit.note'].with_context(
                active_model="account.move",
                active_ids=credit_note.ids
            ).create({
                'date': self.frozen_today,
                'reason': 'no reason',
                'l10n_co_edi_description_code_debit': '4',
            })
            res = move_debit_note_wiz.create_debit()
            debit_note = self.env['account.move'].browse(res.get('res_id'))

            # Check the generated debit note has lines
            self.assertTrue(debit_note.line_ids)

            expected_debit_note_xml = misc.file_open('l10n_co_edi/tests/accepted_debit_note_2.xml', 'rb').read()
            self.l10n_co_assert_generated_file_equal(debit_note, expected_debit_note_xml)
