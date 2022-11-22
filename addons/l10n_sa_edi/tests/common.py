# coding: utf-8
from datetime import datetime

from odoo import Command
from odoo.tests import tagged
from odoo.addons.account_edi.tests.common import AccountEdiTestCommon


@tagged('post_install_l10n', '-at_install', 'post_install')
class TestSaEdiCommon(AccountEdiTestCommon):

    @classmethod
    def setUpClass(cls, chart_template_ref='sa', edi_format_ref='l10n_sa_edi.edi_sa_zatca'):
        super().setUpClass(chart_template_ref=chart_template_ref, edi_format_ref=edi_format_ref)
        # Setup company
        cls.company = cls.company_data['company']
        cls.company.name = 'SA Company Test'
        cls.company.country_id = cls.env.ref('base.sa')
        cls.company.email = "info@company.saexample.com"
        cls.company.phone = '+966 51 234 5678'
        cls.customer_invoice_journal = cls.env['account.journal'].search([('company_id', '=', cls.company.id), ('type', '=', 'sale')], limit=1)
        cls.company.l10n_sa_edi_building_number = '1234'
        cls.company.l10n_sa_edi_plot_identification = '1234'
        cls.company.street2 = "Testomania"
        cls.company.l10n_sa_additional_identification_number = '2525252525252'
        cls.company.l10n_sa_additional_identification_scheme = 'CRN'
        cls.company.vat = '311111111111113'
        cls.company.l10n_sa_private_key = cls.env['res.company']._l10n_sa_generate_private_key()
        cls.company.state_id = cls.env['res.country.state'].create({
            'name': 'Riyadh',
            'code': 'RYA',
            'country_id': cls.company.country_id.id
        })
        cls.company.street = 'Al Amir Mohammed Bin Abdul Aziz Street'
        cls.company.city = 'المدينة المنورة'
        cls.company.zip = '42317'
        cls.customer_invoice_journal.l10n_sa_serial_number = '123456789'
        cls.partner_us = cls.env['res.partner'].create({
            'name': 'Chichi Lboukla',
            'ref': 'Azure Interior',
            'street': '4557 De Silva St',
            'l10n_sa_edi_building_number': '12300',
            'l10n_sa_edi_plot_identification': '2323',
            'l10n_sa_additional_identification_scheme': 'CRN',
            'l10n_sa_additional_identification_number': '353535353535353',
            'city': 'Fremont',
            'zip': '94538',
            'street2': 'Neighbor!',
            'country_id': cls.env.ref('base.us').id,
            'state_id': cls.env['res.country.state'].search([('name', '=', 'California')]).id,
            'email': 'azure.Interior24@example.com',
            'phone': '(870)-931-0505',
            'company_type': 'company',
            'lang': 'en_US',
        })

        cls.partner_sa = cls.env['res.partner'].create({
            'name': 'Chichi Lboukla',
            'ref': 'Azure Interior',
            'street': '4557 De Silva St',
            'l10n_sa_edi_building_number': '12300',
            'l10n_sa_edi_plot_identification': '2323',
            'l10n_sa_additional_identification_scheme': 'CRN',
            'l10n_sa_additional_identification_number': '353535353535353',
            'city': 'Fremont',
            'zip': '94538',
            'street2': 'Neighbor!',
            'country_id': cls.env.ref('base.sa').id,
            'state_id': cls.env['res.country.state'].search([('name', '=', 'California')]).id,
            'email': 'azure.Interior24@example.com',
            'phone': '(870)-931-0505',
            'company_type': 'company',
            'lang': 'en_US',
        })

        cls.partner_sa_simplified = cls.env['res.partner'].create({
            'name': 'Mohammed Ali',
            'ref': 'Mohammed Ali',
            'country_id': cls.env.ref('base.sa').id,
            'l10n_sa_additional_identification_scheme': 'MOM',
            'l10n_sa_additional_identification_number': '3123123213131',
            'state_id': cls.company.state_id.id,
            'company_type': 'person',
            'lang': 'en_US',
        })

        # 15% tax
        cls.tax_15 = cls.env['account.tax'].search([('company_id', '=', cls.company.id), ('amount', '=', 15.0)], limit=1)

        # Large cabinet product
        cls.product_a = cls.env['product.product'].create({
            'name': 'Product A',
            'uom_id': cls.env.ref('uom.product_uom_unit').id,
            'standard_price': 320.0,
            'default_code': 'P0001',
        })
        cls.product_b = cls.env['product.product'].create({
            'name': 'Product B',
            'uom_id': cls.env.ref('uom.product_uom_unit').id,
            'standard_price': 15.8,
            'default_code': 'P0002',
        })

        cls.product_burger = cls.env['product.product'].create({
            'name': 'Burger',
            'uom_id': cls.env.ref('uom.product_uom_unit').id,
            'standard_price': 265.00,
        })

        cls.remove_ubl_extensions_xpath = '''<xpath expr="//*[local-name()='UBLExtensions']" position="replace"/>'''

        cls.invoice_applied_xpath = '''
            <xpath expr="(//*[local-name()='Invoice']/*[local-name()='ID'])[1]" position="replace">
                <ID>___ignore___</ID>
            </xpath>
            <xpath expr="(//*[local-name()='Invoice']/*[local-name()='UUID'])[1]" position="replace">
                <UUID>___ignore___</UUID>
            </xpath>
            <xpath expr="(//*[local-name()='Contact']/*[local-name()='ID'])[1]" position="replace">
                <ID>___ignore___</ID>
            </xpath>
            <xpath expr="(//*[local-name()='Contact']/*[local-name()='ID'])[2]" position="replace">
                <ID>___ignore___</ID>
            </xpath>
            <xpath expr="//*[local-name()='PaymentMeans']/*[local-name()='InstructionID']" position="replace">
                <InstructionID>___ignore___</InstructionID>
            </xpath>
            <xpath expr="(//*[local-name()='PaymentMeans']/*[local-name()='PaymentID'])" position="replace">
                <PaymentID>___ignore___</PaymentID>
            </xpath>
            <xpath expr="//*[local-name()='InvoiceLine']/*[local-name()='ID']" position="replace">
                <ID>___ignore___</ID>
            </xpath>
            '''

        cls.credit_note_applied_xpath = '''
            <xpath expr="(//*[local-name()='Invoice']/*[local-name()='ID'])[1]" position="replace">
                <ID>___ignore___</ID>
            </xpath>
            <xpath expr="(//*[local-name()='Invoice']/*[local-name()='UUID'])[1]" position="replace">
                <UUID>___ignore___</UUID>
            </xpath>
            <xpath expr="(//*[local-name()='Contact']/*[local-name()='ID'])[1]" position="replace">
                <ID>___ignore___</ID>
            </xpath>
            <xpath expr="(//*[local-name()='Contact']/*[local-name()='ID'])[2]" position="replace">
                <ID>___ignore___</ID>
            </xpath>
            <xpath expr="(//*[local-name()='OrderReference']/*[local-name()='ID'])[1]" position="replace">
                <ID>___ignore___</ID>
            </xpath>
            <xpath expr="(//*[local-name()='InvoiceDocumentReference']/*[local-name()='ID'])[1]" position="replace">
                <ID>___ignore___</ID>
            </xpath>
            <xpath expr="(//*[local-name()='PaymentMeans']/*[local-name()='InstructionNote'])" position="replace">
                <InstructionNote>___ignore___</InstructionNote>
            </xpath>
            <xpath expr="(//*[local-name()='PaymentMeans']/*[local-name()='PaymentID'])" position="replace">
                <PaymentID>___ignore___</PaymentID>
            </xpath>
            <xpath expr="//*[local-name()='InvoiceLine']/*[local-name()='ID']" position="replace">
                <ID>___ignore___</ID>
            </xpath>
            '''

        cls.debit_note_applied_xpath = '''
                <xpath expr="(//*[local-name()='Invoice']/*[local-name()='ID'])[1]" position="replace">
                    <ID>___ignore___</ID>
                </xpath>
                <xpath expr="(//*[local-name()='Invoice']/*[local-name()='UUID'])[1]" position="replace">
                    <UUID>___ignore___</UUID>
                </xpath>
                <xpath expr="(//*[local-name()='Contact']/*[local-name()='ID'])[1]" position="replace">
                    <ID>___ignore___</ID>
                </xpath>
                <xpath expr="(//*[local-name()='Contact']/*[local-name()='ID'])[2]" position="replace">
                    <ID>___ignore___</ID>
                </xpath>
                <xpath expr="(//*[local-name()='OrderReference']/*[local-name()='ID'])[1]" position="replace">
                    <ID>___ignore___</ID>
                </xpath>
                <xpath expr="(//*[local-name()='InvoiceDocumentReference']/*[local-name()='ID'])[1]" position="replace">
                    <ID>___ignore___</ID>
                </xpath>
                <xpath expr="//*[local-name()='InvoiceLine']/*[local-name()='ID']" position="replace">
                    <ID>___ignore___</ID>
                </xpath>
                <xpath expr="//*[local-name()='PaymentMeans']/*[local-name()='InstructionID']" position="replace">
                    <InstructionID>___ignore___</InstructionID>
                </xpath>
                <xpath expr="(//*[local-name()='PaymentMeans']/*[local-name()='PaymentID'])" position="replace">
                    <PaymentID>___ignore___</PaymentID>
                </xpath>
                <xpath expr="(//*[local-name()='PaymentMeans']/*[local-name()='InstructionNote'])" position="replace">
                    <InstructionNote>___ignore___</InstructionNote>
                </xpath>
                '''

    def _create_invoice(self, **kwargs):
        vals = {
            'name': kwargs['name'],
            'move_type': 'out_invoice',
            'company_id': self.company.id,
            'partner_id': kwargs['partner_id'].id,
            'invoice_date': kwargs['date'],
            'invoice_date_due': kwargs['date_due'],
            'currency_id': self.company.currency_id.id,
            'invoice_line_ids': [Command.create({
                'product_id': kwargs['product_id'].id,
                'price_unit': kwargs['price'],
                'quantity': kwargs.get('quantity', 1.0),
                'tax_ids': [Command.set(self.tax_15.ids)],
            }),
            ],
        }
        move = self.env['account.move'].create(vals)
        move.state = 'posted'
        move.l10n_sa_confirmation_datetime = datetime.now()
        # move.payment_reference = move.name
        return move

    def _create_debit_note(self, **kwargs):
        invoice = self._create_invoice(**kwargs)

        debit_note_wizard = self.env['account.debit.note'].with_context(
            {'active_ids': [invoice.id], 'active_model': 'account.move', 'default_copy_lines': True}).create({
                'reason': 'Totes forgot'})
        res = debit_note_wizard.create_debit()
        debit_note = self.env['account.move'].browse(res['res_id'])
        debit_note.l10n_sa_confirmation_datetime = datetime.now()
        debit_note.state = 'posted'
        return debit_note

    def _create_credit_note(self, **kwargs):
        move = self._create_invoice(**kwargs)
        move_reversal = self.env['account.move.reversal'].with_context(active_model="account.move", active_ids=move.ids).create({
            'reason': 'no reason',
            'journal_id': move.journal_id.id,
        })
        reversal = move_reversal.reverse_moves()
        reverse_move = self.env['account.move'].browse(reversal['res_id'])
        reverse_move.l10n_sa_confirmation_datetime = datetime.now()
        reverse_move.state = 'posted'
        return reverse_move
