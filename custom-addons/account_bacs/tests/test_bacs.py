# -*- coding: utf-8 -*-

from odoo import fields
from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.addons.account_bacs.models.account_journal import format_communication
from odoo.tests import tagged

import itertools

import datetime

import base64

@tagged('post_install', '-at_install')
class TestBACS(AccountTestInvoicingCommon):

    @classmethod
    def setUpClass(cls, chart_template_ref=None):
        super().setUpClass(chart_template_ref=chart_template_ref)
        cls.env.ref('base.GBP').active = True

        cls.bank_barclays = cls.env['res.bank'].create({
            'name': 'BARCLAYS BANK PLC',
            'bic': 'BARCGB22XXX',
        })
        cls.bank_hsbc = cls.env['res.bank'].create({
            'name': 'HSBC',
            'bic': 'HBUKGB4BXXX',
        })

        cls.company_data['company'].write({
            'country_id': cls.env.ref('base.be').id,
            'bacs_sun': '123456',
        })
        cls.bank_journal = cls.company_data['default_journal_bank']
        cls.bank_journal.write({
            'bank_id': cls.bank_barclays.id,
            'bank_acc_number': 'GB11BARC20039525689371',
            'currency_id': cls.env.ref('base.GBP').id,
        })

        cls.bacs_dc = cls.bank_journal.outbound_payment_method_line_ids.filtered(lambda l: l.code == 'bacs_dc')
        cls.bacs_dc_method = cls.env.ref('account_bacs.payment_method_bacs_dc')

        cls.bacs_dd = cls.bank_journal.inbound_payment_method_line_ids.filtered(lambda l: l.code == 'bacs_dd')
        cls.bacs_dd_method = cls.env.ref('account_bacs.payment_method_bacs_dd')

    def create_account(self, number, partner, bank):
        return self.env['res.partner.bank'].create({
            'acc_number': number,
            'partner_id': partner.id,
            'bank_id': bank.id,
            'allow_out_payment': True,
        })

    def create_ddi(self, partner, partner_bank, company, payment_journal):
        return self.env['bacs.ddi'].create({
            'partner_bank_id': partner_bank.id,
            'start_date': fields.Date.today(),
            'partner_id': partner.id,
            'company_id': company.id,
            'payment_journal_id': payment_journal.id
        })

    def create_invoice(self, partner):
        invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': partner.id,
            'currency_id': self.env.ref('base.GBP').id,
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
        self.env['account.payment.register'].with_context(active_model='account.move', active_ids=invoice.ids).create({
            'payment_date': invoice.invoice_date_due or invoice.invoice_date,
            'journal_id': mandate.payment_journal_id.id,
            'payment_method_line_id': self.bacs_dd.id,
        })._create_payments()

    def create_payment(self, partner, amount, payment_method, journal, date, payment_type, partner_bank=None):
        return self.env['account.payment'].create({
            'journal_id': journal.id,
            'payment_method_line_id': payment_method.id,
            'payment_type': payment_type,
            'date': date,
            'amount': amount,
            'partner_id': partner.id,
            'partner_bank_id': partner_bank.id if partner_bank else False,
        })

    def verify_bacs_file_headers(self, company, batch_payment, header_lines):
        # test vol1
        self.assertEqual(len(header_lines[0]), 80)
        self.assertEqual(header_lines[0][:4], 'VOL1')
        self.assertEqual(header_lines[0][4:10], batch_payment.bacs_submission_serial)
        self.assertEqual(header_lines[0][10:41], ' ' * 31)
        self.assertEqual(header_lines[0][41:47], company.bacs_sun)
        self.assertEqual(header_lines[0][47:79], ' ' * 32)
        self.assertEqual(header_lines[0][79:], '1')
        # test HDR1
        self.assertEqual(len(header_lines[1]), 80)
        self.assertEqual(header_lines[1][:5], 'HDR1A')
        self.assertEqual(header_lines[1][5:11], company.bacs_sun)
        self.assertEqual(header_lines[1][11:15], 'S  1')
        self.assertEqual(header_lines[1][15:21], company.bacs_sun)
        self.assertEqual(header_lines[1][21:27], batch_payment.bacs_submission_serial)
        self.assertEqual(header_lines[1][27:35], '00010001')
        self.assertEqual(header_lines[1][35:41], ' ' * 6)
        self.assertEqual(header_lines[1][41:47], batch_payment.date.strftime(' %y%j'))
        self.assertEqual(header_lines[1][47:53], batch_payment.bacs_expiry_date.strftime(' %y%j'))
        self.assertEqual(header_lines[1][53:], ' ' * 27)
        # test HDR2
        self.assertEqual(len(header_lines[2]), 80)
        self.assertEqual(header_lines[2][:5], 'HDR2F')
        self.assertEqual(header_lines[2][5:10], '02000')
        self.assertEqual(header_lines[2][10:15], '00100')
        self.assertEqual(header_lines[2][15:], ' ' * 65)
        # test UHL1
        self.assertEqual(len(header_lines[3]), 80)
        self.assertEqual(header_lines[3][:4], 'UHL1')
        self.assertEqual(header_lines[3][4:10], ' ' * 6 if batch_payment.bacs_multi_mode else batch_payment.bacs_processing_date.strftime(' %y%j'))
        self.assertEqual(header_lines[3][10:20], company.bacs_sun.ljust(10))
        self.assertEqual(header_lines[3][20:28], '0' * 8)
        self.assertEqual(header_lines[3][28:37], '4 MULTI  ' if batch_payment.bacs_multi_mode else '1 DAILY  ')
        self.assertEqual(header_lines[3][37:], ' ' * 43)

    def verify_contra_line(self, company, payments, contra_line, is_multi, payment_method_code):
        self.assertEqual(len(contra_line), 106 if is_multi else 100)
        self.assertEqual(contra_line[:14], self.bank_journal.bank_account_id.sanitized_acc_number[8:])
        self.assertEqual(contra_line[14:15], '0')
        self.assertEqual(contra_line[15:17], '99' if payment_method_code == 'bacs_dd' else '17')
        self.assertEqual(contra_line[17:31], self.bank_journal.bank_account_id.sanitized_acc_number[8:])
        self.assertEqual(contra_line[31:35], ' ' * 4)
        contra_amount = sum([int(payment.amount * 100) for payment in payments])
        self.assertEqual(contra_line[35:46], str(contra_amount).rjust(11, '0'))
        self.assertEqual(contra_line[64:82], 'CONTRA'.ljust(18))
        self.assertEqual(contra_line[82:100], format_communication(company.name).ljust(18))
        if is_multi:
            self.assertEqual(contra_line[100:], payments[0].date.strftime(' %y%j'))


    def verify_payment_line(self, company, payment, line, is_multi, payment_method_code):
        self.assertEqual(len(line), 106 if is_multi else 100)
        self.assertEqual(line[:14], payment.partner_bank_id.sanitized_acc_number[8:] if payment_method_code == 'bacs_dc' else payment.bacs_ddi_id.partner_bank_id.sanitized_acc_number[8:])
        self.assertEqual(line[14:15], '0')
        self.assertIn(line[15:17], ['01', '17', '18', '19'] if payment_method_code == 'bacs_dd' else ['99'])
        self.assertEqual(line[17:31], self.bank_journal.bank_account_id.sanitized_acc_number[8:])
        self.assertEqual(line[31:35], ' ' * 4)
        self.assertEqual(line[35:46], str(int(payment.amount * 100)).rjust(11, '0'))
        self.assertEqual(line[46:64], format_communication(company.name[:18]).ljust(18))
        self.assertEqual(line[82:100], format_communication(payment.partner_id.name[:18]).ljust(18))
        if is_multi:
            self.assertEqual(line[100:], payment.date.strftime(' %y%j'))

    def verify_bacs_file_payments(self, company, batch_payment, payment_lines):
        if not batch_payment.bacs_multi_mode:
            self.assertEqual(len(payment_lines), len(batch_payment.payment_ids) + 1)
            for i, payment_line in enumerate(payment_lines):
                if i == len(payment_lines) - 1:
                    self.verify_contra_line(company, batch_payment.payment_ids, payment_line, False, batch_payment.payment_method_id.code)
                else:
                    self.verify_payment_line(company, batch_payment.payment_ids[i], payment_line, False, batch_payment.payment_method_id.code)
        else:
            # group payments by date and each date should have tranaction reccords of the date followed by a contra line
            payments_by_date = itertools.groupby(batch_payment.payment_ids.sorted(key=lambda p: p.date), key=lambda p: p.date)
            self.assertEqual(len(payment_lines), len(batch_payment.payment_ids) + len(list(payments_by_date)))
            start = 0
            for _, payments in payments_by_date:
                payments = list(payments)
                for i, payment in enumerate(payments):
                    self.verify_payment_line(company, payment, payment_lines[i + start], True, batch_payment.payment_method_id.code)
                self.verify_contra_line(company, payments, payment_lines[len(payments) + start], True, batch_payment.payment_method_id.code)
                start += len(payments) + 1

    def verify_bacs_file_footers(self, company, batch_payment, footer_lines):
        # test EOF1
        self.assertEqual(len(footer_lines[0]), 80)
        self.assertEqual(footer_lines[0][:5], 'EOF1A')
        self.assertEqual(footer_lines[0][5:11], company.bacs_sun)
        self.assertEqual(footer_lines[0][11:15], 'S  1')
        self.assertEqual(footer_lines[0][15:21], company.bacs_sun)
        self.assertEqual(footer_lines[0][21:27], batch_payment.bacs_submission_serial)
        self.assertEqual(footer_lines[0][27:35], '00010001')
        self.assertEqual(footer_lines[0][35:41], ' ' * 6)
        self.assertEqual(footer_lines[0][41:47], batch_payment.date.strftime(' %y%j'))
        self.assertEqual(footer_lines[0][47:53], batch_payment.bacs_expiry_date.strftime(' %y%j'))
        self.assertEqual(footer_lines[0][53:], ' ' * 27)
        # test EOF2
        self.assertEqual(len(footer_lines[1]), 80)
        self.assertEqual(footer_lines[1][:5], 'EOF2F')
        self.assertEqual(footer_lines[1][5:10], '02000')
        self.assertEqual(footer_lines[1][10:15], '00100')
        self.assertEqual(footer_lines[1][15:], ' ' * 65)
        # test UTL1
        self.assertEqual(len(footer_lines[2]), 80)
        self.assertEqual(footer_lines[2][:4], 'UTL1')
        total = sum([int(payment.amount * 100) for payment in batch_payment.payment_ids])
        self.assertEqual(footer_lines[2][4:17], str(total).rjust(13, '0'))
        self.assertEqual(footer_lines[2][17:30], footer_lines[2][4:17])
        transaction_record_count = str(len(batch_payment.payment_ids)).rjust(7, '0')
        contra_record_count = str(len(set(payment.date for payment in batch_payment.payment_ids))).rjust(7, '0') if batch_payment.bacs_multi_mode else '0000001'
        code = batch_payment.payment_method_id.code
        self.assertEqual(footer_lines[2][30:37], transaction_record_count if code == 'bacs_dd' else contra_record_count)
        self.assertEqual(footer_lines[2][37:44], contra_record_count if code == 'bacs_dd' else transaction_record_count)
        self.assertEqual(footer_lines[2][44:], ' ' * 36)

    def verify_bacs_file(self, company, batch):
        binary_data = base64.b64decode(batch.export_file)
        file_string = binary_data.decode('utf-8')
        split_file = file_string.rstrip('\n').split('\n')
        header_lines = split_file[:4]
        payment_lines = split_file[4:-3]
        footer_lines = split_file[-3:]
        self.assertEqual(len(header_lines), 4, "There should be 4 header lines in the file")
        self.assertEqual(len(footer_lines), 3, "There should be 3 footer lines in the file")
        self.verify_bacs_file_headers(company, batch, header_lines)
        self.verify_bacs_file_payments(company, batch, payment_lines)
        self.verify_bacs_file_footers(company, batch, footer_lines)

    def verify_multi_payments(self, company, partner, multi_mode, payment_method, payment_method_line, payment_type, partner_bank=None):
        payment_1 = self.create_payment(partner, 42, payment_method_line, self.bank_journal, datetime.date.today() + datetime.timedelta(days=10), payment_type, partner_bank)
        payment_1.action_post()
        payment_2 = self.create_payment(partner, 1337, payment_method_line, self.bank_journal, datetime.date.today() + datetime.timedelta(days=15), payment_type, partner_bank)
        payment_2.action_post()
        payment_3 = self.create_payment(partner, 21, payment_method_line, self.bank_journal, datetime.date.today() + datetime.timedelta(days=20), payment_type, partner_bank)
        payment_3.action_post()
        payment_4 = self.create_payment(partner, 1916, payment_method_line, self.bank_journal, datetime.date.today() + datetime.timedelta(days=20), payment_type, partner_bank)
        payment_4.action_post()

        batch = self.env['account.batch.payment'].create({
            'batch_type': payment_type,
            'bacs_processing_date': fields.Date.today(),
            'bacs_multi_mode': multi_mode,
            'payment_ids': [(4, payment.id, None) for payment in [payment_1, payment_2, payment_3, payment_4]],
            'journal_id': self.bank_journal.id,
            'payment_method_id': payment_method.id,
        })
        wizard_action = batch.validate_batch()
        self.assertFalse(wizard_action, "Validation wizard should not have returned an action")
        self.verify_bacs_file(company, batch)

    def testBacsDirectDebit(self):
        company = self.env.company
        partner_boundagani = self.env['res.partner'].create({'name': 'Boundagani'})
        partner_bank_boundagani = self.create_account('GB03BARC20031819726663', partner_boundagani, self.bank_hsbc)
        ddi_boundagani = self.create_ddi(partner_boundagani, partner_bank_boundagani, self.env.company, self.bank_journal)
        ddi_boundagani.action_validate_ddi()
        invoice_boundagani = self.create_invoice(partner_boundagani)
        self.pay_with_mandate(invoice_boundagani, ddi_boundagani)
        payment_boundagani = invoice_boundagani.line_ids.mapped('matched_credit_ids.credit_move_id.payment_id')
        self.assertEqual(invoice_boundagani.payment_state, self.env['account.move']._get_invoice_in_payment_state(), 'This invoice should have been paid thanks to the mandate')
        self.assertEqual(invoice_boundagani.bacs_ddi_id, ddi_boundagani, 'The invoice should have the right mandate')

        # test single payment
        batch = self.env['account.batch.payment'].create({
            'bacs_processing_date': fields.Date.today(),
            'bacs_multi_mode': False,
            'payment_ids': [(4, payment_boundagani.id, None)],
            'journal_id': self.bank_journal.id,
            'payment_method_id': self.bacs_dd_method.id,
            'batch_type': 'inbound',
        })
        wizard_action = batch.validate_batch()
        self.assertFalse(wizard_action, "Validation wizard should not have returned an action")
        self.verify_bacs_file(company, batch)

        # test multi payment with single mode
        self.verify_multi_payments(company, partner_boundagani, False, self.bacs_dd_method, self.bacs_dd, 'inbound')

        # test multi payment with multi mode
        self.verify_multi_payments(company, partner_boundagani, True, self.bacs_dd_method, self.bacs_dd, 'inbound')

    def testBacsDirectCredit(self):
        company = self.env.company
        vendor_superlux = self.env['res.partner'].create({'name': 'Superlux'})
        vendor_bank_superlux = self.create_account('GB70BARC20038066716256', vendor_superlux, self.bank_hsbc)
        payment_superlux = self.create_payment(vendor_superlux, 42, self.bacs_dc, self.bank_journal, datetime.date.today() + datetime.timedelta(days=10), 'outbound', vendor_bank_superlux)
        payment_superlux.action_post()

        # test single payment
        batch = self.env['account.batch.payment'].create({
            'bacs_processing_date': fields.Date.today(),
            'bacs_multi_mode': False,
            'payment_ids': [(4, payment_superlux.id, None)],
            'journal_id': self.bank_journal.id,
            'payment_method_id': self.bacs_dc_method.id,
            'batch_type': 'outbound',
        })
        wizard_action = batch.validate_batch()
        self.assertFalse(wizard_action, "Validation wizard should not have returned an action")
        self.verify_bacs_file(company, batch)

        # test multi payment with single mode
        self.verify_multi_payments(company, vendor_superlux, False, self.bacs_dc_method, self.bacs_dc, 'outbound', vendor_bank_superlux)

        # test multi payment with multi mode
        self.verify_multi_payments(company, vendor_superlux, True, self.bacs_dc_method, self.bacs_dc, 'outbound', vendor_bank_superlux)
