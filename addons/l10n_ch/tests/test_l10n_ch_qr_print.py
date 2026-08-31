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
    @AccountTestInvoicingCommon.setup_country('ch')
    def setUpClass(cls):
        super().setUpClass()
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

    def _create_invoice_partners_with_incomplete_addresses(self):
        self.creditor_partner = self.qr_bank_account.partner_id
        self.creditor_partner.write({
            'name': 'cred partner',
            'country_id': self.env.ref('base.ch').id,
            'zip': 1000,
            'city': False,
            'street': False,
            'street2': False,
            'email': 'creditor@game.odoo.com',
        })
        self.debtor_partner_ch = self.env['res.partner'].create({
            'name': 'deb partner CH',
            'country_id': self.env.ref('base.ch').id,
            'zip': 2000,
            'city': False,
            'street': False,
            'street2': False,
            'email': 'debtor_ch@game.odoo.com',
        })
        self.debtor_partner_li = self.env['res.partner'].create({
            'name': 'deb partner LI',
            'country_id': self.env.ref('base.li').id,
            'zip': 3000,
            'city': False,
            'street': False,
            'street2': False,
            'email': 'debtor_li@game.odoo.com',
        })
        # QR is not generated for non CH/LI partners, no error should be raised for BE
        self.debtor_partner_be = self.env['res.partner'].create({
            'name': 'deb partner BE',
            'country_id': self.env.ref('base.be').id,
            'zip': 4000,
            'city': False,
            'street': False,
            'street2': False,
            'email': 'debtor_be@game.odoo.com',
        })
        self.invoice_ch = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.debtor_partner_ch.id,
            'partner_bank_id': self.qr_bank_account.id,
            'currency_id': self.env.ref('base.CHF').id,
            'invoice_date': '2019-01-01',
            'invoice_line_ids': [(0, 0, {'product_id': self.product_a.id})],
        })
        self.invoice_li = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.debtor_partner_li.id,
            'partner_bank_id': self.qr_bank_account.id,
            'currency_id': self.env.ref('base.CHF').id,
            'invoice_date': '2019-01-01',
            'invoice_line_ids': [(0, 0, {'product_id': self.product_a.id})],
        })
        self.invoice_be = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.debtor_partner_be.id,
            'partner_bank_id': self.qr_bank_account.id,
            'currency_id': self.env.ref('base.CHF').id,
            'invoice_date': '2019-01-01',
            'invoice_line_ids': [(0, 0, {'product_id': self.product_a.id})],
        })
        self.invoices = self.invoice_ch + self.invoice_li + self.invoice_be
        self.invoices.action_post()

    def test_action_single_send_and_print_and_info_message(self):
        """Tests whether the wizard will display an info banner for the missing
            adresses of the debtors(CH/LI) and whether an error will be raised when
            trying to Send & Print with incomplete addresses of debtors(CH/LI) and
            creditors(CH)"""

        self._create_invoice_partners_with_incomplete_addresses()

        self.assertTrue(self.invoice_ch.l10n_ch_is_qr_valid)
        self.assertTrue(self.invoice_li.l10n_ch_is_qr_valid)
        self.assertFalse(self.invoice_be.l10n_ch_is_qr_valid)

        def get_wizard(invoice_id):
            return self.env['account.move.send.wizard'].with_context(
                active_model='account.move',
                active_ids=[invoice_id.id],

                # In test env, the pdf generation is skipped and switches to html
                # rendering. However when company.qr_code is not set, the CH QR
                # code generation is only overriden for pdf rendering.
                # This forces the pdf rendering to simulate the normal behavior.
                force_report_rendering=True,
            ).create({
                'sending_methods': ['email'],
            })

        wizard = get_wizard(self.invoice_ch)
        self.assertEqual(
            wizard.alerts['l10n_ch_partners_without_street']['action']['res_id'],
            self.debtor_partner_ch.id,
        )
        with self.allow_pdf_render():
            self.assertRaisesRegex(UserError,
                "The partner set on the bank account meant to receive "
                "the payment .* must have the necessary postal address "
                "information \\(zip, city and country\\).",
                wizard.action_send_and_print,
            )

        # No error for Belgian partners
        wizard = get_wizard(self.invoice_be)
        self.assertEqual(wizard.alerts, False)
        with self.allow_pdf_render():
            wizard.action_send_and_print()

        self.creditor_partner.write({'city': 'Bern'})
        wizard = get_wizard(self.invoice_ch)
        self.assertEqual(
            wizard.alerts['l10n_ch_partners_without_street']['action']['res_id'],
            self.debtor_partner_ch.id,
        )
        with self.allow_pdf_render():
            self.assertRaisesRegex(UserError,
                "The partner must have the necessary postal address "
                "information \\(zip, city and country\\).",
                wizard.action_send_and_print,
            )

        self.debtor_partner_ch.write({'city': 'Martigny'})
        wizard = get_wizard(self.invoice_ch)
        self.assertEqual(
            wizard.alerts['l10n_ch_partners_without_street']['action']['res_id'],
            self.debtor_partner_ch.id,
        )
        with self.allow_pdf_render():
            wizard.action_send_and_print()

        self.debtor_partner_li.write({'city': 'Vaduz'})
        wizard = get_wizard(self.invoice_li)
        self.assertEqual(
            wizard.alerts['l10n_ch_partners_without_street']['action']['res_id'],
            self.debtor_partner_li.id,
        )
        with self.allow_pdf_render():
            wizard.action_send_and_print()

        self.debtor_partner_ch.write({'street': 'Street Name 1'})
        wizard = get_wizard(self.invoice_ch)
        self.assertEqual(wizard.alerts, False)
        with self.allow_pdf_render():
            wizard.action_send_and_print()

        self.debtor_partner_li.write({'street': 'Street Name 2'})
        wizard = get_wizard(self.invoice_li)
        self.assertEqual(wizard.alerts, False)
        with self.allow_pdf_render():
            wizard.action_send_and_print()

    def test_action_batch_send_and_print_and_info_message(self):
        """
        Tests whether the wizard will display an info banner for the missing
        adresses of the debtors(CH/LI).
        Tests that the cron job of a Batch Send & Print is not blocked for
        all invoices when encountering a file with QR Code errors (incomplete
        addresses of debtors(CH/LI) and creditors(CH)).
        Tests whether the pdf invoices will be generated for the valid
        invoices
        """

        self._create_invoice_partners_with_incomplete_addresses()

        self.assertTrue(self.invoice_ch.l10n_ch_is_qr_valid)
        self.assertTrue(self.invoice_li.l10n_ch_is_qr_valid)
        self.assertFalse(self.invoice_be.l10n_ch_is_qr_valid)

        account_move_send_cron = self.env.ref('account.ir_cron_account_move_send')

        def get_batch_wizard(invoice_ids):
            return self.env['account.move.send.batch.wizard'].with_context(
                active_model='account.move',
                active_ids=invoice_ids.ids,
            ).create({})

        def run_move_send_cron():
            with self.allow_pdf_render():
                account_move_send_cron.method_direct_trigger()

        batch_wizard = get_batch_wizard(self.invoices)
        self.assertEqual(
            batch_wizard.alerts['l10n_ch_partners_without_street']['action']['domain'][0][2],
            [self.debtor_partner_ch.id, self.debtor_partner_li.id],
        )
        # No invoice is generated or sent yet
        self.assertEqual(self.invoices.mapped(lambda inv: bool(inv.invoice_pdf_report_id)), [False] * len(self.invoices))
        # Invoices are not in the queue yet
        self.assertEqual(self.invoices.mapped(lambda inv: bool(inv.sending_data)), [False] * len(self.invoices))
        batch_wizard.action_send_and_print()
        # All 3 invoices are registered for sending now
        self.assertEqual(self.invoices.mapped(lambda inv: bool(inv.sending_data)), [True] * len(self.invoices))

        run_move_send_cron()

        # Both Ch and Li invoices are affected by the issue, Be is sent normally.
        self.assertFalse(self.invoice_ch.invoice_pdf_report_id)
        self.assertFalse(self.invoice_li.invoice_pdf_report_id)
        self.assertTrue(self.invoice_be.invoice_pdf_report_id)
        # All invoices are either sent and/or removed from queue
        self.assertEqual(self.invoices.mapped(lambda inv: bool(inv.sending_data)), [False] * len(self.invoices))

        self.creditor_partner.write({'city': 'Bern'})
        batch_wizard = get_batch_wizard(self.invoices)
        self.assertEqual(
            batch_wizard.alerts['l10n_ch_partners_without_street']['action']['domain'][0][2],
            [self.debtor_partner_ch.id, self.debtor_partner_li.id],
        )
        batch_wizard.action_send_and_print()
        run_move_send_cron()
        self.assertFalse(self.invoice_ch.invoice_pdf_report_id)
        self.assertFalse(self.invoice_li.invoice_pdf_report_id)
        # All invoices are either sent and/or removed from queue
        self.assertEqual(self.invoices.mapped(lambda inv: bool(inv.sending_data)), [False] * len(self.invoices))

        self.debtor_partner_ch.write({'city': 'Martigny'})
        batch_wizard = get_batch_wizard(self.invoices)
        self.assertEqual(
            batch_wizard.alerts['l10n_ch_partners_without_street']['action']['domain'][0][2],
            [self.debtor_partner_ch.id, self.debtor_partner_li.id],
        )
        batch_wizard.action_send_and_print()
        run_move_send_cron()
        self.assertTrue(self.invoice_ch.invoice_pdf_report_id)
        self.assertFalse(self.invoice_li.invoice_pdf_report_id)
        self.assertEqual(self.invoices.mapped(lambda inv: bool(inv.sending_data)), [False] * len(self.invoices))

        self.debtor_partner_li.write({'city': 'Vaduz'})
        batch_wizard = get_batch_wizard(self.invoices)
        self.assertEqual(
            batch_wizard.alerts['l10n_ch_partners_without_street']['action']['domain'][0][2],
            [self.debtor_partner_ch.id, self.debtor_partner_li.id],
        )
        batch_wizard.action_send_and_print()
        run_move_send_cron()
        self.assertTrue(self.invoice_li.invoice_pdf_report_id)
        self.assertEqual(self.invoices.mapped(lambda inv: bool(inv.sending_data)), [False] * len(self.invoices))
        self.assertEqual(self.invoices.mapped(lambda inv: bool(inv.invoice_pdf_report_id)), [True] * len(self.invoices))

        self.debtor_partner_ch.write({'street': 'Street Name 1'})
        batch_wizard = get_batch_wizard(self.invoices)
        self.assertEqual(
            batch_wizard.alerts['l10n_ch_partners_without_street']['action']['res_id'],
            self.debtor_partner_li.id,
        )
        batch_wizard.action_send_and_print()

        self.debtor_partner_li.write({'street': 'Street Name 2'})
        batch_wizard = get_batch_wizard(self.invoices)
        self.assertEqual(batch_wizard.alerts, False)
        batch_wizard.action_send_and_print()
