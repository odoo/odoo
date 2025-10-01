# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo.addons.l10n_latam_check.tests.common import L10nLatamCheckTest
from odoo.exceptions import ValidationError, UserError
from odoo.tests.common import tagged
from odoo import fields, Command


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestThirdChecks(L10nLatamCheckTest):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.new_third_party_check_payment_method = cls.env['account.payment.method'].create({
            'name': 'Test New Third Party Check',
            'code': 'new_third_party_checks',
            'payment_type': 'inbound',
        })

        cls.in_third_party_check_payment_method = cls.env['account.payment.method'].create({
            'name': 'Test New Third Party Check',
            'code': 'in_third_party_checks',
            'payment_type': 'inbound',
        })

        cls.out_third_party_check_payment_method = cls.env['account.payment.method'].create({
            'name': 'Test New Third Party Check',
            'code': 'out_third_party_checks',
            'payment_type': 'outbound',
        })

    def create_third_party_check(self, journal=False, check_numbers=['00000001', '00000002']):
        if not journal:
            journal = self.third_party_check_journal
        vals = {
            'partner_id': self.partner_a.id,
            'payment_type': 'inbound',
            'journal_id': journal.id,
            'l10n_latam_new_check_ids': [
                Command.create({'name': check_numbers[0], 'payment_date': fields.Date.add(fields.Date.today(), months=1), 'amount': 1}),
                Command.create({'name': check_numbers[1], 'payment_date': fields.Date.add(fields.Date.today(), months=1), 'amount': 1}),
            ],
            'payment_method_id': self.get_payment_methods('new_third_party_checks', self.env.company).id,
        }

        payment = self.env['account.payment'].create(vals)
        payment.action_post()
        return payment

    def test_01_get_paid_with_multiple_checks(self):
        """ This a generic test to check that we are able to pay with checks
        We pay directly with multiple checks instead of just one check, just to ensure the create multi
        is properly working. """
        payment = self.create_third_party_check()

        self.assertEqual(len(payment.l10n_latam_new_check_ids), 2, 'Checks where not created properly')
        self.assertRecordValues(payment.l10n_latam_new_check_ids, [{
            'current_journal_id': self.third_party_check_journal.id,
        }]*2)

    # delivery (assert) dd un cheque tmb un return (assert) y un claim (assert)
    def test_02_third_party_check_delivery(self):
        payment = self.create_third_party_check()
        check = payment.l10n_latam_new_check_ids[0]
        # Check Delivery
        vals = {
            'l10n_latam_move_check_ids': [Command.set([check.id])],
            'partner_id': self.partner_a.id,
            'payment_type': 'outbound',
            'journal_id': self.third_party_check_journal.id,
            'payment_method_id': self.get_payment_methods(('out_third_party_checks'), self.env.company).id,
        }
        delivery = self.env['account.payment'].create(vals)
        delivery.action_post()
        self.assertFalse(check.current_journal_id, 'Current journal was not computed properly on delivery')
        # check dont delivery twice
        with self.assertRaisesRegex(ValidationError, "it seems it has been moved by another payment"):
            self.env['account.payment'].create(vals).action_post()

        # Check Return / Rejection
        vals = {
            'l10n_latam_move_check_ids': [Command.set([check.id])],
            'amount': 1,
            'partner_id': self.partner_a.id,
            'payment_type': 'inbound',
            'journal_id': self.rejected_check_journal.id,
            'payment_method_id': self.get_payment_methods('in_third_party_checks', self.env.company).id,
        }
        supplier_return = self.env['account.payment'].create(vals)
        supplier_return.action_post()
        self.assertEqual(check.current_journal_id, self.rejected_check_journal, 'Current journal was not computed properly on return')
        # check dont return twice
        with self.assertRaisesRegex(ValidationError, "Some checks are already in hand and can't be received again"):
            self.env['account.payment'].create(vals).action_post()

        # Check Claim/Return to customer
        vals = {
            'l10n_latam_move_check_ids': [Command.set([check.id])],
            'partner_id': self.partner_a.id,
            'payment_type': 'outbound',
            'journal_id': self.rejected_check_journal.id,
            'payment_method_id': self.get_payment_methods(('out_third_party_checks'), self.env.company).id,
        }
        customer_return = self.env['account.payment'].create(vals)
        customer_return.action_post()
        self.assertFalse(check.current_journal_id, 'Current journal was not computed properly on customer return')
        # check dont claim twice
        with self.assertRaisesRegex(ValidationError, "Some checks are not anymore in journal,"):
            self.env['account.payment'].create(vals).action_post()

        operations = self.env['account.payment'].search([('l10n_latam_move_check_ids', '=', check.id), ('state', '!=', 'draft')], order="date desc, id desc")
        self.assertEqual(len(operations), 3, 'There should be 3 operations on the check')
        self.assertEqual(operations, customer_return | supplier_return | delivery)

    def test_03_deposit(self):
        payment = self.create_third_party_check()
        check = payment.l10n_latam_new_check_ids[0]
        bank_journal = self.ar_company_data['default_journal_bank']

        # Deposit the check to the bank
        self.env['l10n_latam.payment.mass.transfer'].with_context(
            active_model='l10n_latam.check', active_ids=[check.id]
        ).create({
            'destination_journal_id': bank_journal.id,
        })._create_payments()
        self.assertEqual(check.current_journal_id.id, bank_journal.id, 'Current journal was not computed properly on delivery')
        self.assertEqual(len(check.operation_ids + payment), 3, 'Check that all three payments were created')

        # If the bank tells you that the check has been rejected you have to do a new transfer of the previous check
        self.env['l10n_latam.payment.mass.transfer'].with_context(
            active_model='l10n_latam.check', active_ids=[check.id]
        ).create({
            'destination_journal_id': self.rejected_check_journal.id,
        })._create_payments()
        self.assertEqual(check.current_journal_id.id, self.rejected_check_journal.id, 'Current journal was not computed properly on delivery')
        self.assertEqual(len(check.operation_ids + payment), 5, 'Check that all five payments were created')

        # Sent back to customer (with payment) - check if we can use the check
        self.env['account.payment'].create({
            'partner_id': self.partner_a.id,
            'payment_type': 'outbound',
            'journal_id': self.rejected_check_journal.id,
            'l10n_latam_move_check_ids': [Command.set([check.id])],
            'payment_method_id': self.get_payment_methods('new_third_party_checks', self.env.company).id,
        }).action_post()

    def test_04_check_transfer(self):
        """ Test transfer between third party checks journals """
        payment = self.create_third_party_check()
        check = payment.l10n_latam_new_check_ids[0]

        # Transfer to rejected checks journal (usually is to another third party checks journal, but for test purpose is the same)
        self.env['l10n_latam.payment.mass.transfer'].with_context(
            active_model='l10n_latam.check', active_ids=[check.id]).create({'destination_journal_id': self.rejected_check_journal.id})._create_payments()
        self.assertEqual(check.current_journal_id, self.rejected_check_journal, 'Current journal was not computed properly on delivery')

        # test that checks created on different journals but that are on same current journal, can be transfered together
        payment2 = self.create_third_party_check(journal=self.rejected_check_journal)
        check2 = payment2.l10n_latam_new_check_ids[0]
        self.env['l10n_latam.payment.mass.transfer'].with_context(
            active_model='l10n_latam.check', active_ids=[check.id, check2.id]).create({'destination_journal_id': self.third_party_check_journal.id})._create_payments()

    def test_available_journals_for_third_party_checks(self):
        '''When new/in/out third party check payment methods are chosen only cash journals should be available in the payment form,
        and when a bank journal is chosen these same payment methods should not be available.'''

        for method, payment_type in [('new_third_party_checks', 'inbound'), ('in_third_party_checks', 'inbound'), ('out_third_party_checks', 'outbound')]:
            payment1 = self.env['account.payment'].with_company(self.ar_company).create({
                'payment_method_id': self.get_payment_methods(method, self.ar_company).id,
                'partner_id': self.partner_a.id,
                'payment_type': payment_type,
                'journal_id': self.third_party_check_journal.id,
                'l10n_latam_new_check_ids': [
                    Command.create({'name': '00000001', 'payment_date': fields.Date.add(fields.Date.today(), months=1), 'amount': 1}),
                    Command.create({'name': '00000002', 'payment_date': fields.Date.add(fields.Date.today(), months=1), 'amount': 1}),
                ],
            })
            self.assertEqual(set(payment1.available_journal_ids.mapped('type')), {'cash'})

            payment2 = self.env['account.payment'].with_company(self.ar_company).create({
                'partner_id': self.partner_a.id,
                'payment_type': payment_type,
                'journal_id': self.bank_journal.id,
                'l10n_latam_new_check_ids': [
                    Command.create({'name': '00000003', 'payment_date': fields.Date.add(fields.Date.today(), months=1), 'amount': 1}),
                    Command.create({'name': '00000004', 'payment_date': fields.Date.add(fields.Date.today(), months=1), 'amount': 1}),
                ],
            })
            self.assertFalse(method in payment2.available_payment_method_ids.mapped('code'))
