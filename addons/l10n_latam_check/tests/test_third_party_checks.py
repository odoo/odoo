# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo.addons.l10n_latam_check.tests.common import L10nLatamCheckTest
from odoo.exceptions import ValidationError, UserError
from odoo.tests.common import tagged


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestThirdChecks(L10nLatamCheckTest):

    def create_third_party_check(self, journal=False):
        if not journal:
            journal = self.third_party_check_journal
        vals = {
            'partner_id': self.partner_a.id,
            'amount': 1,
            'check_number': '00000001',
            'payment_type': 'inbound',
            'journal_id': journal.id,
            'payment_method_line_id': self.third_party_check_journal._get_available_payment_method_lines('inbound').filtered(lambda x: x.code == 'new_third_party_checks').id,
        }
        payment = self.env['account.payment'].create(vals)
        payment.action_post()
        return payment

    def test_01_get_paid_with_multiple_checks(self):
        """ This a generic test to check that we are able to pay with checks
        We pay directly with multiple checks instead of just one check, just to ensure the create multi
        is properly working. """
        vals_list = [{
            'partner_id': self.partner_a.id,
            'amount': 1,
            'check_number': '00000001',
            'payment_type': 'inbound',
            'journal_id': self.third_party_check_journal.id,
            'payment_method_line_id': self.third_party_check_journal._get_available_payment_method_lines('inbound').filtered(lambda x: x.code == 'new_third_party_checks').id,
        }, {
            'partner_id': self.partner_a.id,
            'amount': 2,
            'check_number': '00000002',
            'payment_type': 'inbound',
            'journal_id': self.third_party_check_journal.id,
            'payment_method_line_id': self.third_party_check_journal._get_available_payment_method_lines('inbound').filtered(lambda x: x.code == 'new_third_party_checks').id,
        }]
        payments = self.env['account.payment'].create(vals_list)
        payments.action_post()
        self.assertEqual(len(payments), 2, 'Checks where not created properly')
        self.assertRecordValues(payments, [{
            'l10n_latam_check_current_journal_id': self.third_party_check_journal.id,
        }]*2)

    def test_02_third_party_check_delivery(self):
        check = self.create_third_party_check()

        # Check Delivery
        vals = {
            'l10n_latam_check_id': check.id,
            'amount': 1,
            'partner_id': self.partner_a.id,
            'payment_type': 'outbound',
            'journal_id': self.third_party_check_journal.id,
            'payment_method_line_id': self.third_party_check_journal._get_available_payment_method_lines('outbound').filtered(lambda x: x.code == 'out_third_party_checks').id,
        }
        delivery = self.env['account.payment'].create(vals)
        delivery.action_post()
        self.assertFalse(check.l10n_latam_check_current_journal_id, 'Current journal was not computed properly on delivery')
        # check dont delivery twice
        with self.assertRaisesRegex(ValidationError, "it seems it has been moved by another payment"), self.cr.savepoint():
            self.env['account.payment'].create(vals).action_post()

        # Check Return / Rejection
        vals = {
            'l10n_latam_check_id': check.id,
            'amount': 1,
            'partner_id': self.partner_a.id,
            'payment_type': 'inbound',
            'journal_id': self.rejected_check_journal.id,
            'payment_method_line_id': self.rejected_check_journal._get_available_payment_method_lines('inbound').filtered(lambda x: x.code == 'in_third_party_checks').id,
        }
        supplier_return = self.env['account.payment'].create(vals)
        supplier_return.action_post()
        self.assertEqual(check.l10n_latam_check_current_journal_id, self.rejected_check_journal, 'Current journal was not computed properly on return')
        # check dont return twice
        with self.assertRaisesRegex(ValidationError, "it can't be received it again"), self.cr.savepoint():
            self.env['account.payment'].create(vals).action_post()

        # Check Claim/Return to customer
        vals = {
            'l10n_latam_check_id': check.id,
            'amount': 1,
            'partner_id': self.partner_a.id,
            'payment_type': 'outbound',
            'journal_id': self.rejected_check_journal.id,
            'payment_method_line_id': self.rejected_check_journal._get_available_payment_method_lines('outbound').filtered(lambda x: x.code == 'out_third_party_checks').id,
        }
        customer_return = self.env['account.payment'].create(vals)
        customer_return.action_post()
        self.assertFalse(check.l10n_latam_check_current_journal_id, 'Current journal was not computed properly on customer return')
        # check dont claim twice
        with self.assertRaisesRegex(ValidationError, "it seems it has been moved by another payment"), self.cr.savepoint():
            self.env['account.payment'].create(vals).action_post()

        operations = self.env['account.payment'].search([('l10n_latam_check_id', '=', check.id), ('state', '=', 'posted')], order="date desc, id desc")
        self.assertEqual(len(operations), 3, 'There should be 3 operations on the check')
        self.assertEqual(operations, customer_return | supplier_return | delivery)

    def test_03_check_deposit(self):
        check = self.create_third_party_check()
        bank_journal = self.company_data_3['default_journal_bank']

        # Check Deposit
        deposit = self.env['l10n_latam.payment.mass.transfer'].with_context(
            active_model='account.payment', active_ids=[check.id]).create({'destination_journal_id': bank_journal.id})._create_payments()
        self.assertEqual(check.l10n_latam_check_current_journal_id, bank_journal, 'Current journal was not computed properly on delivery')
        # check dont deposit twice
        with self.assertRaisesRegex(UserError, "All selected checks must be on the same journal and on hand"), self.cr.savepoint():
            self.env['l10n_latam.payment.mass.transfer'].with_context(
                active_model='account.payment', active_ids=[check.id]).create({'destination_journal_id': bank_journal.id})._create_payments()

        # Check Rejection
        vals = {
            'l10n_latam_check_id': check.id,
            'amount': 1,
            'payment_type': 'inbound',
            'journal_id': self.rejected_check_journal.id,
            'is_internal_transfer': True,
            'payment_method_line_id': self.rejected_check_journal._get_available_payment_method_lines('inbound').filtered(lambda x: x.code == 'in_third_party_checks').id,
            'destination_journal_id': bank_journal.id,
        }
        bank_rejection = self.env['account.payment'].create(vals)
        bank_rejection.action_post()
        self.assertEqual(check.l10n_latam_check_current_journal_id, self.rejected_check_journal, 'Current journal was not computed properly on return')
        # check dont reject twice
        with self.assertRaisesRegex(ValidationError, "it seems it has been moved by another payment"), self.cr.savepoint():
            self.env['account.payment'].create(vals).action_post()

        # Check Claim/Return to customer
        vals = {
            'l10n_latam_check_id': check.id,
            'amount': 1,
            'partner_id': self.partner_a.id,
            'payment_type': 'outbound',
            'journal_id': self.rejected_check_journal.id,
            'payment_method_line_id': self.rejected_check_journal._get_available_payment_method_lines('outbound').filtered(lambda x: x.code == 'out_third_party_checks').id,
        }
        customer_return = self.env['account.payment'].create(vals)
        customer_return.action_post()
        self.assertFalse(check.l10n_latam_check_current_journal_id, 'Current journal was not computed properly on customer return')
        # check dont return twice
        with self.assertRaisesRegex(ValidationError, "it seems it has been moved by another payment"), self.cr.savepoint():
            self.env['account.payment'].create(vals).action_post()

        operations = self.env['account.payment'].search([('l10n_latam_check_id', '=', check.id), ('state', '=', 'posted')], order="date desc, id desc")
        # we have 5 operations because for each transfers a second payment/operation is created automatically by odoo
        self.assertEqual(len(operations), 5, 'There should be 5 operations on the check')
        self.assertEqual(operations[0], customer_return, 'Last operation should be customer return')
        self.assertEqual(operations[2], bank_rejection, 'Previous operation should be bank rejection')
        self.assertEqual(operations[4], deposit, 'First operation should be the deposit')

    def test_04_check_transfer(self):
        """ Test transfer between third party checks journals """
        check = self.create_third_party_check()

        # Transfer to rejected checks journal (usually is to another third party checks journal, but for test purpose is the same)
        self.env['l10n_latam.payment.mass.transfer'].with_context(
            active_model='account.payment', active_ids=[check.id]).create({'destination_journal_id': self.rejected_check_journal.id})._create_payments()
        self.assertEqual(check.l10n_latam_check_current_journal_id, self.rejected_check_journal, 'Current journal was not computed properly on delivery')

        # test that checks created on different journals but that are on same current journal, can be transfered together
        check2 = self.create_third_party_check(journal=self.rejected_check_journal)
        self.env['l10n_latam.payment.mass.transfer'].with_context(
            active_model='account.payment', active_ids=[check.id, check2.id]).create({'destination_journal_id': self.third_party_check_journal.id})._create_payments()
