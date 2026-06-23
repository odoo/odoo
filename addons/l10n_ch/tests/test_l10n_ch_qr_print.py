# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import logging

from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.exceptions import UserError
from odoo.tests import tagged

_logger = logging.getLogger(__name__)

@tagged('post_install_l10n', 'post_install', '-at_install')
class QRPrintTest(AccountTestInvoicingCommon):

    @classmethod
    def setUpClass(cls, chart_template_ref='ch'):
        super().setUpClass(chart_template_ref=chart_template_ref)
        # the partner must be located in Switzerland.
        cls.partner = cls.env['res.partner'].create({
            'name': 'Bobby',
            'country_id': cls.env.ref('base.ch').id,
        })
        # The bank account must be QR-compatible
        cls.qr_bank_account = cls.env['res.partner.bank'].create({
            'acc_number': "CH4431999123000889012",
            'partner_id': cls.env.company.partner_id.id,
            'allow_out_payment': True,
        })
        cls.correct_invoice_chf = cls.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': cls.partner.id,
            'partner_bank_id': cls.qr_bank_account.id,
            'currency_id': cls.env.ref('base.CHF').id,
            'invoice_date': '2019-01-01',
            'invoice_line_ids': [(0, 0, {'product_id': cls.product_a.id})],
        })

        cls.correct_invoice_eur = cls.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': cls.partner.id,
            'partner_bank_id': cls.qr_bank_account.id,
            'currency_id': cls.env.ref('base.EUR').id,
            'invoice_date': '2019-01-01',
            'invoice_line_ids': [(0, 0, {'product_id': cls.product_a.id})],
        })

        cls.wrong_partner_invoice = cls.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': cls.partner_a.id,
            'partner_bank_id': cls.qr_bank_account.id,
            'currency_id': cls.env.ref('base.EUR').id,
            'invoice_date': '2019-01-01',
            'invoice_line_ids': [(0, 0, {'product_id': cls.product_a.id})],
        })

    def print_qr_bill(self, invoice):
        try:
            invoice.action_invoice_sent()
            return True
        except UserError as e:
            _logger.warning(str(e))
            return False

    def test_print_qr(self):
        self.correct_invoice_chf.action_post()
        self.assertTrue(self.print_qr_bill(self.correct_invoice_chf))

        #The QR can also be printed if the currency is EUR
        self.env.ref('base.EUR').active = True
        self.correct_invoice_eur.action_post()
        self.assertTrue(self.print_qr_bill(self.correct_invoice_eur))

        #A normal invoice will be printed if the partner is not from Switzerland
        self.wrong_partner_invoice.action_post()
        self.assertTrue(self.print_qr_bill(self.wrong_partner_invoice))

        #However, a qr bill can't be printed with those infos
        self.assertFalse(self.wrong_partner_invoice.l10n_ch_is_qr_valid)

    def test_action_send_and_print_and_info_message(self):
        """Tests whether the wizard will display an info banner for the missing
            adresses of the debtors and whether an error will be raised when
            trying to Send & Print with incomplete addresses of debtors and
            creditors"""

        creditor_partner = self.qr_bank_account.partner_id
        creditor_partner.write({
            'name': 'cred partner',
            'country_id': self.env.ref('base.ch').id,
            'zip': 1000,
            'city': False,
            'street': False,
            'street2': False,
        })
        debtor_partner_1 = self.env['res.partner'].create({
            'name': 'deb partner 1',
            'country_id': self.env.ref('base.ch').id,
            'zip': 2000,
            'city': False,
            'street': False,
            'street2': False,
        })
        debtor_partner_2 = self.env['res.partner'].create({
            'name': 'deb partner 2',
            'country_id': self.env.ref('base.ch').id,
            'zip': 3000,
            'city': False,
            'street': False,
            'street2': False,
        })
        invoice_1 = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': debtor_partner_1.id,
            'partner_bank_id': self.qr_bank_account.id,
            'currency_id': self.env.ref('base.CHF').id,
            'invoice_date': '2019-01-01',
            'invoice_line_ids': [(0, 0, {'product_id': self.product_a.id})],
        })
        invoice_2 = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': debtor_partner_2.id,
            'partner_bank_id': self.qr_bank_account.id,
            'currency_id': self.env.ref('base.CHF').id,
            'invoice_date': '2019-01-01',
            'invoice_line_ids': [(0, 0, {'product_id': self.product_a.id})],
        })
        invoices = invoice_1 + invoice_2
        invoices.action_post()

        def get_wizard():
            return self.env['account.move.send'].with_context(active_model='account.move', active_ids=invoices.ids).create({})

        self.env.company.qr_code = True

        wizard = get_wizard()
        self.assertEqual(wizard.partners_without_street.ids, [debtor_partner_1.id, debtor_partner_2.id])
        self.assertRaisesRegex(UserError,
            "The partner set on the bank account meant to receive "
            "the payment .* must have the necessary postal address "
            "information \\(zip, city and country\\).",
            wizard.action_send_and_print,
        )

        creditor_partner.write({'city': 'Bern'})
        wizard = get_wizard()
        self.assertEqual(wizard.partners_without_street.ids, [debtor_partner_1.id, debtor_partner_2.id])
        self.assertRaisesRegex(UserError,
            "The partner must have the necessary postal address "
            "information \\(zip, city and country\\).",
            wizard.action_send_and_print,
        )

        debtor_partner_1.write({'city': 'Martigny'})
        wizard = get_wizard()
        self.assertEqual(wizard.partners_without_street.ids, [debtor_partner_1.id, debtor_partner_2.id])
        self.assertRaisesRegex(UserError,
            "The partner must have the necessary postal address "
            "information \\(zip, city and country\\).",
            wizard.action_send_and_print,
        )

        debtor_partner_2.write({'city': 'Geneva'})
        wizard = get_wizard()
        self.assertEqual(wizard.partners_without_street.ids, [debtor_partner_1.id, debtor_partner_2.id])
        wizard.action_send_and_print()

        debtor_partner_1.write({'street': 'Street Name 1'})
        wizard = get_wizard()
        self.assertEqual(wizard.partners_without_street.ids, [debtor_partner_2.id])
        wizard.action_send_and_print()

        debtor_partner_2.write({'street': 'Street Name 2'})
        wizard = get_wizard()
        self.assertEqual(wizard.partners_without_street.ids, [])
        wizard.action_send_and_print()
