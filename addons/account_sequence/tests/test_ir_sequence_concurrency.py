# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import psycopg2

from odoo import SUPERUSER_ID, api, fields
from odoo.tests import tagged
from odoo.tools import mute_logger
from odoo.addons.account.tests.test_sequence_mixin import TestSequenceMixinConcurrency


@tagged('post_install', '-at_install', 'test_ir_sequence_concurrency')
class TestIrSequenceConcurrency(TestSequenceMixinConcurrency):
    """
    Tests for the sequence_account module.
    When the sequence_id is set on account.journal, names will be computed based on the sequence.
    If the sequence is set to no_gap implementation the behaviour will be the same as before,
    if the sequence is set to standard implementation, there will have more flexibility on concurrent
    creations of moves but gaps can then occur in sequence.
    """

    def setUp(self):
        super().setUp()
        with self.env.registry.cursor() as cr:
            env = api.Environment(cr, SUPERUSER_ID, {})
            ir_sequences = env['ir.sequence'].create([{
                'name': 'Account Ir Sequence Test',
                'code': 'account.ir.sequence.test',
                'prefix': 'PrefixTest/',
                'padding': 4,
            }] * 3)

            invoices = env['account.move'].create([{
                "move_type": "out_invoice",
                "partner_id": self.env.ref("base.res_partner_12").id,
                'invoice_date': fields.Date.from_string('2016-01-01'),
                "invoice_line_ids": [(0, 0, {
                    'quantity': 1,
                    'price_unit': 600,
                    'tax_ids': [],
                })]
            }] * 3)
            invoices[0].action_post()
            self.assertEqual(invoices.mapped('name'), ['INV/2016/00001', '/', '/'])

            payments = env['account.payment'].create([{
                'payment_type': 'inbound',
                'payment_method_id': self.env.ref('account.account_payment_method_manual_in').id,
                'partner_type': 'customer',
                'partner_id': self.env.ref("base.res_partner_12").id,
                'date': fields.Date.from_string('2016-01-01'),
                'amount': 600,
            }] * 3)
            payments[0].action_post()
            self.assertEqual(payments.mapped('name'), ['PBNK1/2016/00001', '/', '/'])

            journal = env['account.journal'].browse(self.data['journal_id'])
            journal.sequence_id = ir_sequences[0]
            journal_inv = invoices.journal_id
            journal_inv.sequence_id = ir_sequences[1]
            journal_pay = payments.journal_id
            journal_pay.sequence_id = ir_sequences[2]
            env.cr.commit()

        self.data['sequence_ids'] = ir_sequences.ids
        self.data['payment_ids'] = payments.ids
        self.data['invoice_ids'] = invoices.ids
        self.data['journal_pay_id'] = journal_pay.id
        self.data['journal_inv_id'] = journal_inv.id
        self.addCleanup(self.cleanUpIr)

    def cleanUpIr(self):
        with self.env.registry.cursor() as cr:
            env = api.Environment(cr, SUPERUSER_ID, {})
            payments = env['account.payment'].browse(self.data['payment_ids'])
            payments.action_draft()
            payments.unlink()

            invoices = env['account.move'].browse(self.data['invoice_ids'])
            invoices.button_draft()
            invoices.posted_before = False
            invoices.with_context(force_delete=True).unlink()

            journal = env['account.journal'].browse(self.data['journal_id'])
            journal.sequence_id = False
            journal_pay = env['account.journal'].browse(self.data['journal_pay_id'])
            journal_pay.sequence_id = False
            journal_inv = env['account.journal'].browse(self.data['journal_inv_id'])
            journal_inv.sequence_id = False

            ir_sequences = env['ir.sequence'].browse(self.data['sequence_ids'])
            ir_sequences.unlink()
            env.cr.commit()

    def _set_sequences_impl(self, impl='standard'):
        """Changes test sequences implementation to `impl`
        :param impl: the implementation we want to use"""
        with self.env.registry.cursor() as cr:
            env = api.Environment(cr, SUPERUSER_ID, {})
            ir_sequences = env['ir.sequence'].browse(self.data['sequence_ids'])
            ir_sequences.implementation = impl
            env.cr.commit()

    def test_sequence_concurency(self):
        # OVERRIDE
        """Computing the same name in concurrent transactions is not allowed with no_gap implementation."""
        self._set_sequences_impl('no_gap')
        env0, env1, env2 = self.data['envs']

        # start the transactions here on cr1 to simulate concurrency with cr2
        env1.cr.execute('SELECT 1')

        # post in cr2
        move = env2['account.move'].browse(self.data['move_ids'][1])
        move.action_post()
        env2.cr.commit()

        # try to post in cr1, should fail because this transaction started before the post in cr2
        move = env1['account.move'].browse(self.data['move_ids'][2])
        with self.assertRaises(psycopg2.OperationalError), mute_logger('odoo.sql_db'):
            move.action_post()

        # check the values
        moves = env0['account.move'].browse(self.data['move_ids'])
        self.assertEqual(moves.mapped('name'), ['CT/2016/01/0001', 'PrefixTest/0001', '/'])

    def test_sequence_concurrency_standard(self):
        """Posting in concurrent transactions is allowed with standard implementation of sequences"""
        env0, env1, env2 = self.data['envs']

        # start the transactions here on cr1 to simulate concurrency with cr2
        env1.cr.execute('SELECT 1')

        # post in cr2
        move = env2['account.move'].browse(self.data['move_ids'][1])
        move.action_post()
        env2.cr.commit()

        # try to post in cr1, should work but could create holes (standard implementation)
        move = env1['account.move'].browse(self.data['move_ids'][2])
        move.action_post()
        env1.cr.commit()

        # Check the values
        moves = env0['account.move'].browse(self.data['move_ids'])
        # Everything should be posted
        self.assertNotEqual(moves.mapped('name'), ['/', '/', '/'])

    def test_sequence_concurency_no_useless_lock(self):
        # OVERRIDE
        """Do not lock needlessly when the sequence is not computed"""
        self._set_sequences_impl('no_gap')
        env0, env1, env2 = self.data['envs']

        # start the transactions here on cr1 to simulate concurrency with cr2
        env1.cr.execute('SELECT 1')

        # get the last sequence in cr1 (for instance opening a form view)
        move = env2['account.move'].browse(self.data['move_ids'][1])
        move.highest_name
        env2.cr.commit()

        # post in cr1, should work even though cr2 read values
        move = env1['account.move'].browse(self.data['move_ids'][2])
        move.action_post()
        env1.cr.commit()

        # check the values
        moves = env0['account.move'].browse(self.data['move_ids'])
        self.assertEqual(moves.mapped('name'), ['CT/2016/01/0001', '/', 'PrefixTest/0001'])

    def test_sequence_concurrency_no_useless_lock_standard(self):
        """Do not lock needlessly when the sequence is not computed"""
        env0, env1, env2 = self.data['envs']

        # start the transactions here on cr1 to simulate concurrency with cr2
        env1.cr.execute('SELECT 1')

        # get the last sequence in cr1 (for instance opening a form view)
        move = env2['account.move'].browse(self.data['move_ids'][1])
        move.highest_name
        env2.cr.commit()

        # post in cr1, should work even though cr2 read values
        move = env1['account.move'].browse(self.data['move_ids'][2])
        move.action_post()
        env1.cr.commit()

        # check the values
        moves = env0['account.move'].browse(self.data['move_ids'])
        self.assertEqual(moves[0].name, 'CT/2016/01/0001')
        self.assertEqual(moves[1].name, '/')
        # since holes are allowed, the move is posted but name may not be the next
        self.assertNotEqual(moves[2].name, '/')

    def test_sequence_concurrency_edit_last_move(self):
        """Edit last move and create another one should not raise errors
        with sequence's standard implementation"""
        env0, env1, env2 = self.data['envs']

        # start the transactions here on cr1 to simulate concurrency with cr2
        env1.cr.execute('SELECT 1')

        # Edit the last move in cr2
        move1 = env2['account.move'].browse(self.data['move_ids'][0])
        move1.write({"write_uid": env2.uid})
        env2.cr.commit()

        # Post a new move in cr1
        move2 = env1['account.move'].browse(self.data['move_ids'][1])
        move2.action_post()
        env1.cr.commit()

        # Check values
        moves = env0['account.move'].browse([move1.id, move2.id])
        self.assertEqual(moves.mapped('name'), ['CT/2016/01/0001', 'PrefixTest/0001'])

    def test_sequence_concurrency_edit_last_payment(self):
        """Edit last payment and create another one should not raise errors
        with sequence's standard implementation"""
        env0, env1, env2 = self.data['envs']

        # start the transactions here on cr1 to simulate concurrency with cr2
        env1.cr.execute('SELECT 1')

        # Edit last payment in cr2
        payment1 = env2['account.payment'].browse(self.data['payment_ids'][0])
        payment_move = payment1.move_id
        payment_move.write({"write_uid": env2.uid})
        env2.cr.commit()

        # Post a new payment in cr1
        payment2 = env1['account.payment'].browse(self.data['payment_ids'][1])
        payment2.action_post()
        env1.cr.commit()

        # Check values
        payments = env0['account.payment'].browse([payment1.id, payment2.id])
        self.assertEqual(payments.mapped('name'), ['PBNK1/2016/00001', 'PrefixTest/0001'])

    def test_sequence_concurrency_reconcile_move(self):
        """Reconcile last move and create another one should not raise errors
        with sequence's standard implementation"""
        env0, env1, env2 = self.data['envs']

        # start the transactions here on cr1 to simulate concurrency with cr2
        env1.cr.execute('SELECT 1')

        # Reconcile invoice and payment in cr2
        invoice1 = env2['account.move'].browse(self.data['invoice_ids'][0])
        payment = env2['account.payment'].browse(self.data['payment_ids'][0])
        lines2reconcile = (invoice1 + payment.move_id).line_ids.filtered(
            lambda line: line.account_id.name == 'Account Receivable'
        )
        lines2reconcile.reconcile()
        env2.cr.commit()

        # Post new invoice in cr1
        invoice2 = env1['account.move'].browse(self.data['invoice_ids'][1])
        invoice2.action_post()
        env1.cr.commit()

        # Check values
        moves = env0['account.move'].browse(self.data['invoice_ids'])
        self.assertEqual(moves.mapped('name'), ['INV/2016/00001', 'PrefixTest/0001', '/'])

    def test_sequence_concurrency_payments(self):
        """Posting concurrent payments should not raise errors
        with sequence's standard implementation"""
        env0, env1, env2 = self.data['envs']

        # start the transactions here on cr1 to simulate concurrency with cr2
        env1.cr.execute('SELECT 1')

        # Post new payment in cr2
        payment1 = env2['account.payment'].browse(self.data['payment_ids'][1])
        payment1.action_post()
        env2.cr.commit()

        # Post another payment in cr1
        payment2 = env1['account.payment'].browse(self.data['payment_ids'][2])
        payment2.action_post()
        env1.cr.commit()

        # Check values
        payments = env0['account.payment'].browse(self.data['payment_ids'])
        # Everything should be posted
        self.assertNotEqual(payments.mapped('name'), ['/', '/', '/'])
