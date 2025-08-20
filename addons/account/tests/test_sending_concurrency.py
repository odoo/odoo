# -*- coding: utf-8 -*-

import psycopg2

from odoo import fields, api, Command, SUPERUSER_ID
from odoo.tests import tagged, TransactionCase
from odoo.exceptions import UserError


@tagged('post_install', '-at_install')
class TestSendingConcurrency(TransactionCase):
    def setUp(self):
        super().setUp()
        with self.env.registry.cursor() as cr:
            env = api.Environment(cr, SUPERUSER_ID, {})
            journal = env['account.journal'].create({
                'name': 'concurency_test',
                'code': 'CT',
                'type': 'general',
            })
            account = env['account.account'].create({
                'code': 'CT',
                'name': 'CT',
                'account_type': 'asset_fixed',
            })
            move = env['account.move'].create({
                'journal_id': journal.id,
                'date': fields.Date.from_string('2016-01-01'),
                'line_ids': [Command.create({'name': 'name', 'account_id': account.id})]
            })
            move.action_post()
            env.cr.commit()
            env.cr.close()

        self.data = {
            'move_id': move.id,
            'account_id': account.id,
            'journal_id': journal.id,
        }
        self.envs = []
        self.addCleanup(self.cleanUp)

    def cleanUp(self):
        with self.env.registry.cursor() as cr:
            env = api.Environment(cr, SUPERUSER_ID, {})
            move = env['account.move'].browse(self.data['move_id'])
            move.filtered(lambda x: x.state in ('posted', 'cancel')).button_draft()
            move.posted_before = False
            move.unlink()
            journal = env['account.journal'].browse(self.data['journal_id'])
            journal.unlink()
            account = env['account.account'].browse(self.data['account_id'])
            account.unlink()
            env.cr.commit()

        for env in self.envs:
            env.cr.close()

    def test_sending_concurrency(self):
        """ An imaginary scenario where two users are sending the same invoice,
        performing an external API call, at the same time.

        Normally Odoo should prevent this from happening, but as you can see,
        it doesn't.
        """
        # We define some helpers to simulate the external API call and the lock acquisition.
        def check_move_can_be_sent(move):
            """ This method pretends to be a check on whether the invoice was already sent.
            Typically a method that sends the invoice needs to do this before sending the invoice.
            """
            # Here we hijack the `is_move_sent` field for the purpose of this test.
            return not move.is_move_sent

        def acquire_lock(move):
            """ This method acquires a lock on the invoice in the current transaction.
            Typically a method that sends the invoice needs to do this before sending the invoice.
            """
            move.env.cr.execute(
                f'SELECT * FROM account_move WHERE id IN %s FOR UPDATE SKIP LOCKED',
                [tuple(move.ids)]
            )
            available_ids = {r[0] for r in move.env.cr.fetchall()}
            all_locked = available_ids == set(move.ids)
            if not all_locked:
                raise UserError("Some documents are being sent by another process already.")

        def acquire_lock_v2(move):
            with move.env.cr.savepoint(flush=False):
                try:
                    move.env.cr.execute('SELECT * FROM account_move WHERE id = %s FOR UPDATE NOWAIT', [move.id])
                except psycopg2.errors.LockNotAvailable:
                    raise UserError("Some documents are being sent by another process already.")

        def send_move(move):
            """ This method pretends to be a method that does an API call. """
            pass
        
        def write_api_call_result(move):
            """ After performing the API call, we write the result on the account.move. """
            move.is_move_sent = True

        # Now, we can test the scenario, calling the helpers on the same move, but in different transactions.

        # 1. User 1 starts a transaction
        env0 = api.Environment(self.env.registry.cursor(), SUPERUSER_ID, {})
        self.envs.append(env0)
        move_env0 = env0['account.move'].browse(self.data['move_id'])

        # 2. User 1 checks whether the invoice can be sent.
        self.assertTrue(check_move_can_be_sent(move_env0))

        # 3. User 1 acquires the lock on the invoice.
        acquire_lock(move_env0)

        # 4. User 1 sends the invoice.
        send_move(move_env0)

        # 5. User 2 starts a transaction
        env1 = api.Environment(self.env.registry.cursor(), SUPERUSER_ID, {})
        self.envs.append(env1)
        move_env1 = env1['account.move'].browse(self.data['move_id'])

        # 6. User 2 checks whether the invoice can be sent.
        self.assertTrue(check_move_can_be_sent(move_env1))

        # 7. User 1 writes the result of the API call.
        write_api_call_result(move_env0)

        # 8. User 1 commits the transaction.
        env0.cr.commit()

        # 9. User 2 acquires the lock on the invoice.
        acquire_lock(move_env1)

        # 10. User 2 sends the invoice.
        send_move(move_env1)

        # 11. User 2 writes the result of the API call.
        write_api_call_result(move_env1)

        # 12. User 2 commits the transaction.
        env1.cr.commit()
