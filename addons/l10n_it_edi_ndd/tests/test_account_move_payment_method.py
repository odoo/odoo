from lxml import etree

from odoo import Command
from odoo.tests import tagged
from odoo.addons.l10n_it_edi.tests.common import TestItEdi


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestItAccountMovePaymentMethod(TestItEdi):

    def test_account_move_payment_method(self):
        move = self.init_invoice("out_invoice", amounts=[1000], post=True)
        # When the move is created we put the default value MP05
        self.assertEqual(move.l10n_it_payment_method, 'MP05')

        payment_method = self.env['account.payment.method'].sudo().create({
            'name': 'Test Payment Method',
            'code': 'test_payment_method',
            'payment_type': 'inbound',
        })

        new_payment_method_line = self.env['account.payment.method.line'].create({
            'name': 'new payment method line',
            'payment_method_id': payment_method.id,
            'journal_id': self.company_data['default_journal_bank'].id,
            'l10n_it_payment_method': 'MP07',
        })

        # When registering a payment with a payment method, the payment method on the move will be overwritten
        self.env['account.payment.register'].with_context(
            active_model='account.move',
            active_ids=move.ids,
        ).create({
            'payment_method_line_id': new_payment_method_line.id,
        })._create_payments()

        self.assertEqual(move.l10n_it_payment_method, 'MP07')

    def test_export_riba_customer_iban(self):
        """ With RiBa (MP12) the exported IBAN is the customer's one, not the company's """
        customer_bank = self.env['res.partner.bank'].create({
            'partner_id': self.italian_partner_a.id,
            'acc_number': 'IT60X0542811101000000123456',
        })
        invoice = self.env['account.move'].with_company(self.company).create({
            'move_type': 'out_invoice',
            'invoice_date': '2022-03-24',
            'partner_id': self.italian_partner_a.id,
            'partner_bank_id': self.test_bank.id,
            'invoice_line_ids': [Command.create({
                'name': 'line',
                'price_unit': 100.0,
                'tax_ids': [Command.set(self.default_tax.ids)],
            })],
        })
        invoice.action_post()

        def get_payment_details(invoice):
            tree = etree.fromstring(invoice._l10n_it_edi_render_xml())
            return (
                tree.findtext('.//DettaglioPagamento/ModalitaPagamento'),
                tree.findtext('.//DettaglioPagamento/IBAN'),
            )

        invoice.l10n_it_payment_method = 'MP05'
        self.assertEqual(invoice._l10n_it_edi_get_values()['partner_bank'], self.test_bank)

        invoice.l10n_it_payment_method = 'MP12'
        self.assertEqual(invoice._l10n_it_edi_get_values()['partner_bank'], customer_bank)
        self.assertEqual(get_payment_details(invoice), ('MP12', customer_bank.sanitized_acc_number))

        customer_bank.unlink()
        self.assertFalse(invoice._l10n_it_edi_get_values()['partner_bank'])
        self.assertEqual(get_payment_details(invoice), ('MP12', None))
