from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.models import Model
from odoo.tests import Form, tagged
from odoo import fields, Command
from odoo.exceptions import UserError, RedirectWarning
from unittest.mock import patch


@tagged('post_install', '-at_install')
class TestAccountMoveInalterableHash(AccountTestInvoicingCommon):
    @classmethod
    def setUpClass(cls, chart_template_ref=None):
        super().setUpClass(chart_template_ref=chart_template_ref)

    def _send(self, moves, hash_version=False):
        wizard = self.env['account.move.send'].create({'move_ids': [Command.set(moves.ids)]})
        if hash_version:
            wizard.with_context(hash_version=hash_version).action_send_and_print(force_synchronous=True)
        else:
            wizard.action_send_and_print(force_synchronous=True)

    def _init_and_send(self, vals, hash_version=False, secure_sequence=None):
        moves = self.env['account.move']
        for val in vals:
            move = self.init_invoice("out_invoice", val['partner'], val['date'], amounts=val['amounts'], post=True)
            if secure_sequence:  # Simulate old behavior (pre hash v4)
                move.secure_sequence_number = secure_sequence.next_by_id()
            moves |= move
        self._send(moves, hash_version)
        return moves

    def _reverse_move(self, move):
        reversal = move._reverse_moves()
        reversal.action_post()
        return reversal

    def _get_secure_sequence(self):
        """Before hash v4, we had a secure_sequence on hashed journals.
        We removed it starting v4, however, to test previous versions, we need to create it
        to mock the old behavior."""
        return self.env['ir.sequence'].create({
            'name': 'SECURE_SEQUENCE',
            'code': 'SECURE_SEQUENCE',
            'implementation': 'no_gap',
            'prefix': '',
            'suffix': '',
            'padding': 0,
            'company_id': self.company_data['company'].id,
        })

    def _verify_integrity(self, moves, expected_msg_cover, expected_first_move=None, expected_last_move=None, prefix=None):
        integrity_check = moves.company_id._check_hash_integrity()['results']
        name = prefix or moves[0].sequence_prefix
        integrity_check = next(filter(lambda r: name in r.get('journal_name'), integrity_check))
        self.assertRegex(integrity_check['msg_cover'], expected_msg_cover)
        if expected_first_move and expected_last_move:
            self.assertEqual(integrity_check['first_move_name'], expected_first_move.name)
            self.assertEqual(integrity_check['last_move_name'], expected_last_move.name)

    def test_account_move_inalterable_hash(self):
        """Test that we cannot alter a field used for the computation of the inalterable hash"""
        self.company_data['default_journal_sale'].restrict_mode_hash_table = True
        self.company_data['default_journal_purchase'].restrict_mode_hash_table = True
        move = self._init_and_send([{'partner': self.partner_a, 'date': '2023-01-01', 'amounts': [1000]}])
        in_invoice = self.init_invoice("in_invoice", self.partner_a, "2023-01-01", amounts=[1000], post=True)
        self._send(in_invoice)
        self.assertFalse(in_invoice.inalterable_hash)
        in_invoice.button_hash()
        self.assertNotEqual(in_invoice.inalterable_hash, False)

        common = "This document is protected by a hash. Therefore, you cannot edit the following fields:"
        with self.assertRaisesRegex(UserError, f"{common}.*Inalterability Hash."):
            move.inalterable_hash = 'fake_hash'
        # out_invoice should be hashed on sending, while in_invoice should be hashed manually
        with self.assertRaisesRegex(UserError, f"{common}.*Inalterability Hash."):
            in_invoice.inalterable_hash = "fake_hash"
        with self.assertRaisesRegex(UserError, f"{common}.*Number."):
            move.name = "fake name"
        with self.assertRaisesRegex(UserError, f"{common}.*Date."):
            move.date = fields.Date.from_string('2023-01-02')
        with self.assertRaisesRegex(UserError, f"{common}.*Company."):
            move.company_id = 666
        with self.assertRaisesRegex(UserError, f"{common}(.*Company.*Date.)|(.*Date.*Company.)"):
            move.write({
                'company_id': 666,
                'date': fields.Date.from_string('2023-01-03')
            })

        with self.assertRaisesRegex(UserError, "You cannot edit the following fields.*Account.*"):
            move.line_ids[0].account_id = move.line_ids[1]['account_id']
        with self.assertRaisesRegex(UserError, "You cannot edit the following fields.*Partner.*"):
            move.line_ids[0].partner_id = 666

        # The following fields are not part of the hash so they can be modified
        move.ref = "bla"
        move.line_ids[0].date_maturity = fields.Date.from_string('2023-01-02')

    def test_account_move_hash_integrity_report(self):
        """Test the hash integrity report"""
        moves = self._init_and_send([
            {'partner': self.partner_a, 'date': '2023-01-02', 'amounts': [1000, 2000]},
            {'partner': self.partner_b, 'date': '2023-01-01', 'amounts': [1000, 2000]},
        ])

        # No records to be hashed because the restrict mode is not activated yet
        for result in moves.company_id._check_hash_integrity()['results']:
            self.assertEqual(result['status'], 'not_restricted')

        self.company_data['default_journal_sale'].restrict_mode_hash_table = True

        # Everything should be correctly hashed and verified
        # First sequence
        first_chain_moves = moves | self._init_and_send([
            {'partner': self.partner_a, 'date': '2023-01-03', 'amounts': [1000, 2000]},
            {'partner': self.partner_b, 'date': '2023-01-05', 'amounts': [1000, 2000]},
            {'partner': self.partner_a, 'date': '2023-01-04', 'amounts': [1000, 2000]},  # We don't care about the date order, just the sequence_prefix and sequence_number
            {'partner': self.partner_b, 'date': '2023-01-06', 'amounts': [1000, 2000]},
            {'partner': self.partner_a, 'date': '2023-01-07', 'amounts': [1000, 2000]},
        ])
        moves = first_chain_moves
        self._verify_integrity(moves, "Entries are correctly hashed", moves[0], moves[-1])

        # Second sequence
        second_chain_moves_first_move = self.init_invoice("out_invoice", self.partner_a, "2023-01-08", amounts=[1000, 2000])
        second_chain_moves_first_move.name = "XYZ/1"
        second_chain_moves_first_move.action_post()
        self._send(second_chain_moves_first_move)
        second_chain_moves = (
            second_chain_moves_first_move
            | self._init_and_send([
                {'partner': self.partner_b, 'date': '2023-01-09', 'amounts': [1000, 2000]},
                {'partner': self.partner_a, 'date': '2023-01-12', 'amounts': [1000, 2000]},
                {'partner': self.partner_b, 'date': '2023-01-11', 'amounts': [1000, 2000]},
                {'partner': self.partner_a, 'date': '2023-01-12', 'amounts': [1000, 2000]},
            ])
        )

        # First sequence again
        first_chain_moves_new_move = self.init_invoice("out_invoice", self.partner_a, "2023-01-08", amounts=[1000, 2000])
        first_chain_moves_new_move.name = first_chain_moves[-1].name[:-1] + str(int(first_chain_moves[-1].name[-1]) + 1)
        first_chain_moves_new_move.action_post()
        self._send(first_chain_moves_new_move)
        first_chain_moves |= first_chain_moves_new_move

        # Verification of the two chains.
        moves = first_chain_moves | second_chain_moves
        self._verify_integrity(moves, "Entries are correctly hashed", first_chain_moves[0], first_chain_moves[-1], 'INV/')
        self._verify_integrity(moves, "Entries are correctly hashed", second_chain_moves[0], second_chain_moves[-1], 'XYZ/')

        # Let's change one of the fields used by the hash. It should be detected by the integrity report.
        # We need to bypass the write method of account.move to do so.
        date_hashed = first_chain_moves[3].date
        Model.write(first_chain_moves[3], {'date': fields.Date.from_string('2023-02-07')})
        self._verify_integrity(moves, f'Corrupted data on journal entry with id {first_chain_moves[3].id}.*')

        # Revert the previous change
        Model.write(first_chain_moves[3], {'date': date_hashed})
        self._verify_integrity(moves, "Entries are correctly hashed", first_chain_moves[0], first_chain_moves[-1], 'INV/')

        # Let's try with the one of the subfields
        Model.write(second_chain_moves[-1].line_ids[0], {'partner_id': self.partner_b.id})
        self._verify_integrity(moves, f'Corrupted data on journal entry with id {second_chain_moves[-1].id}.*', prefix='XYZ/')

        # Let's try with the inalterable_hash field itself
        Model.write(first_chain_moves[-1].line_ids[0], {'partner_id': self.partner_a.id})  # Revert the previous change
        Model.write(first_chain_moves[-1], {'inalterable_hash': 'fake_hash'})
        self._verify_integrity(moves, f'Corrupted data on journal entry with id {first_chain_moves[-1].id}.*', prefix='INV/')

    def test_account_move_hash_versioning_1(self):
        """We are updating the hash algorithm. We want to make sure that we do not break the integrity report.
        This test focuses on the case where the user has only moves with the old hash algorithm."""
        self.company_data['default_journal_sale'].restrict_mode_hash_table = True
        secure_sequence = self._get_secure_sequence()
        moves = self._init_and_send([
            {'partner': self.partner_a, 'date': '2023-01-03', 'amounts': [1000, 2000]},
            {'partner': self.partner_b, 'date': '2023-01-02', 'amounts': [1000, 2000]},
            {'partner': self.partner_b, 'date': '2023-01-04', 'amounts': [1000, 2000]},
        ], hash_version=1, secure_sequence=secure_sequence)

        self._verify_integrity(moves, "Entries are correctly hashed", moves[0], moves[-1], prefix=moves[0].sequence_prefix)

        # Let's change one of the fields used by the hash. It should be detected by the integrity report
        # independently of the hash version used. I.e. we first try the v1 hash, then the v2 hash and neither should work.
        # We need to bypass the write method of account.move to do so.
        Model.write(moves[1], {'date': fields.Date.from_string('2023-01-07')})
        self._verify_integrity(moves, f'Corrupted data on journal entry with id {moves[1].id}.*', prefix=moves[0].sequence_prefix)

    def test_account_move_hash_versioning_2(self):
        """We are updating the hash algorithm. We want to make sure that we do not break the integrity report.
        This test focuses on the case where the user has only moves with the new hash algorithm."""
        self.company_data['default_journal_sale'].restrict_mode_hash_table = True
        secure_sequence = self._get_secure_sequence()
        moves = self._init_and_send([
            {'partner': self.partner_a, 'date': '2023-01-01', 'amounts': [1000, 2000]},
            {'partner': self.partner_b, 'date': '2023-01-03', 'amounts': [1000, 2000]},
            {'partner': self.partner_b, 'date': '2023-01-02', 'amounts': [1000, 2000]},
        ], hash_version=2, secure_sequence=secure_sequence)

        self._verify_integrity(moves, "Entries are correctly hashed", moves[0], moves[-1], prefix=moves[0].sequence_prefix)

        # Let's change one of the fields used by the hash. It should be detected by the integrity report
        # independently of the hash version used. I.e. we first try the v1 hash, then the v2 hash and neither should work.
        # We need to bypass the write method of account.move to do so.
        Model.write(moves[1], {'date': fields.Date.from_string('2023-01-07')})
        self._verify_integrity(moves, f'Corrupted data on journal entry with id {moves[1].id}.*', prefix=moves[0].sequence_prefix)

    def test_account_move_hash_versioning_v1_to_v2(self):
        """We are updating the hash algorithm. We want to make sure that we do not break the integrity report.
        This test focuses on the case where the user has moves with both hash algorithms."""
        self.company_data['default_journal_sale'].restrict_mode_hash_table = True
        secure_sequence = self._get_secure_sequence()
        moves_v1 = self._init_and_send([
            {'partner': self.partner_a, 'date': '2023-01-01', 'amounts': [1000, 2000]},
            {'partner': self.partner_b, 'date': '2023-01-03', 'amounts': [1000, 2000]},
            {'partner': self.partner_b, 'date': '2023-01-02', 'amounts': [1000, 2000]},
        ], hash_version=1, secure_sequence=secure_sequence)

        fields_v1 = moves_v1.with_context(hash_version=1)._get_integrity_hash_fields()
        moves_v2 = self._init_and_send([
            {'partner': self.partner_a, 'date': '2023-01-03', 'amounts': [1000, 2000]},
            {'partner': self.partner_b, 'date': '2023-01-02', 'amounts': [1000, 2000]},
            {'partner': self.partner_b, 'date': '2023-01-01', 'amounts': [1000, 2000]},
        ], hash_version=2, secure_sequence=secure_sequence)

        fields_v2 = moves_v2._get_integrity_hash_fields()
        self.assertNotEqual(fields_v1, fields_v2)  # Make sure two different hash algorithms were used

        moves = moves_v1 | moves_v2
        self._verify_integrity(moves, "Entries are correctly hashed", moves[0], moves[-1], prefix=moves[0].sequence_prefix)

        # Let's change one of the fields used by the hash. It should be detected by the integrity report
        # independently of the hash version used. I.e. we first try the v1 hash, then the v2 hash and neither should work.
        # We need to bypass the write method of account.move to do so.
        date_hashed = moves[4].date
        Model.write(moves[4], {'date': fields.Date.from_string('2023-01-07')})
        self._verify_integrity(moves, f'Corrupted data on journal entry with id {moves[4].id}.*', prefix=moves[0].sequence_prefix)

        # Let's revert the change and make sure that we cannot use the v1 after the v2.
        # This means we don't simply check whether the move is correctly hashed with either algorithms,
        # but that we can only use v2 after v1 and not go back to v1 afterwards.
        Model.write(moves[4], {'date': date_hashed})  # Revert the previous change
        moves_v1_bis = self._init_and_send([
            {'partner': self.partner_a, 'date': '2023-01-10', 'amounts': [1000, 2000]},
            {'partner': self.partner_b, 'date': '2023-01-11', 'amounts': [1000, 2000]},
            {'partner': self.partner_b, 'date': '2023-01-12', 'amounts': [1000, 2000]},
        ], hash_version=1, secure_sequence=secure_sequence)
        self._verify_integrity(moves, f'Corrupted data on journal entry with id {moves_v1_bis[0].id}.*', prefix=moves[0].sequence_prefix)

    def test_account_move_hash_versioning_3(self):
        """
        Version 2 does not take into account floating point representation issues.
        Test that version 3 covers correctly this case
        """
        self.company_data['default_journal_sale'].restrict_mode_hash_table = True
        secure_sequence = self._get_secure_sequence()
        moves = self._init_and_send([
            {'partner': self.partner_a, 'date': '2023-01-01', 'amounts': [30 * 0.17, 2000]},
            {'partner': self.partner_b, 'date': '2023-01-03', 'amounts': [1000, 2000]},
            {'partner': self.partner_b, 'date': '2023-01-02', 'amounts': [1000, 2000]},
        ], hash_version=3, secure_sequence=secure_sequence)

        # invalidate cache
        moves[0].line_ids[0].invalidate_recordset()

        self._verify_integrity(moves, "Entries are correctly hashed", moves[0], moves[-1], prefix=moves[0].sequence_prefix)

    def test_account_move_hash_versioning_v2_to_v3(self):
        """
        We are updating the hash algorithm. We want to make sure that we do not break the integrity report.
        This test focuses on the case with version 2 and version 3.
        """
        self.company_data['default_journal_sale'].restrict_mode_hash_table = True
        secure_sequence = self._get_secure_sequence()
        moves_v2 = self._init_and_send([
            {'partner': self.partner_a, 'date': '2023-01-01', 'amounts': [1000, 2000]},
            {'partner': self.partner_b, 'date': '2023-01-03', 'amounts': [1000, 2000]},
            {'partner': self.partner_b, 'date': '2023-01-03', 'amounts': [1000, 2000]},
        ], hash_version=2, secure_sequence=secure_sequence)

        moves_v3 = self._init_and_send([
            {'partner': self.partner_a, 'date': '2023-01-02', 'amounts': [1000, 2000]},
            {'partner': self.partner_b, 'date': '2023-01-01', 'amounts': [1000, 2000]},
            {'partner': self.partner_b, 'date': '2023-01-03', 'amounts': [1000, 2000]},
        ], hash_version=3, secure_sequence=secure_sequence)

        moves = moves_v2 | moves_v3
        self._verify_integrity(moves, "Entries are correctly hashed", moves[0], moves[-1], prefix=moves[0].sequence_prefix)

        Model.write(moves[1], {'date': fields.Date.from_string('2023-01-07')})
        self._verify_integrity(moves, f'Corrupted data on journal entry with id {moves[1].id}.*', prefix=moves[0].sequence_prefix)

    def test_account_move_hash_with_cash_rounding(self):
        # Enable inalterable hash
        self.company_data['default_journal_sale'].restrict_mode_hash_table = True
        # Required for `invoice_cash_rounding_id` to be visible in the view
        self.env.user.groups_id += self.env.ref('account.group_cash_rounding')
        # Test 'add_invoice_line' rounding
        invoice = self.init_invoice('out_invoice', products=self.product_a+self.product_b)
        move_form = Form(invoice)
        # Add a cash rounding having 'add_invoice_line'.
        move_form.invoice_cash_rounding_id = self.cash_rounding_a
        with move_form.invoice_line_ids.edit(0) as line_form:
            line_form.price_unit = 999.99
        move_form.save()

        # Should not raise
        invoice.action_post()
        wizard = self.env['account.move.send'].with_context(active_model='account.move', active_ids=invoice.ids).create({})
        wizard.action_send_and_print()

        self.assertEqual(invoice.amount_total, 1410.0)
        self.assertEqual(invoice.amount_untaxed, 1200.0)
        self.assertEqual(invoice.amount_tax, 210)
        self.assertEqual(len(invoice.invoice_line_ids), 2)
        self.assertEqual(len(invoice.line_ids), 6)

    def test_retroactive_hashing(self):
        """The hash should be retroactive even to moves that were created before the restrict mode was activated."""
        move1 = self.init_invoice("out_invoice", self.partner_a, "2024-01-01", amounts=[1000], post=True)
        self.assertFalse(move1.inalterable_hash)

        self.company_data['default_journal_sale'].restrict_mode_hash_table = True

        move2 = self.init_invoice("out_invoice", self.partner_a, "2024-01-02", amounts=[1000], post=True)
        self._send(move2)

        self.assertNotEqual(move2.inalterable_hash, False)
        self.assertNotEqual(move1.inalterable_hash, False)
        self._verify_integrity(move1 | move2, "Entries are correctly hashed", move1, move2)

    def test_retroactive_hashing_backwards_compatibility(self):
        """
        Simulate old version where the hash was not retroactive
        We should not consider these moves now either
        We should hash after the last moved hashed
        """
        move1 = self.init_invoice("out_invoice", self.partner_a, "2024-01-01", amounts=[1000], post=True)

        self.company_data['default_journal_sale'].restrict_mode_hash_table = True

        move2 = self.init_invoice("out_invoice", self.partner_a, "2024-01-02", amounts=[1000], post=True)

        self._send(move2)  # Computes the hash for both move1 and move2

        Model.write(move1, {'inalterable_hash': False, 'secure_sequence_number': 0})

        move3 = self.init_invoice("out_invoice", self.partner_a, "2024-01-02", amounts=[1000], post=True)
        move3.button_hash()  # Should only compute the hash for move3, not move1 (move2 is already hashed)

        self.assertNotEqual(move3.inalterable_hash, False)
        self.assertFalse(move1.inalterable_hash)

    def test_no_hash_if_hole_in_sequence(self):
        """If there is a hole in the sequence, we should not hash the moves"""
        self.company_data['default_journal_sale'].restrict_mode_hash_table = True
        move1 = self.init_invoice("out_invoice", self.partner_a, "2024-01-01", amounts=[1000], post=True)
        move2 = self.init_invoice("out_invoice", self.partner_a, "2024-01-02", amounts=[1000], post=True)
        move3 = self.init_invoice("out_invoice", self.partner_a, "2024-01-02", amounts=[1000], post=True)

        move2.button_draft()  # Create hole in sequence
        with self.assertRaisesRegex(UserError, "An error occurred when computing the inalterability. A gap has been detected in the sequence."), self.env.cr.savepoint():
            self._send(move3)

        move2.action_post()
        self._send(move3)  # Shouldn't raise

        for move in (move1, move2, move3):
            self.assertNotEqual(move.inalterable_hash, False)

        move4 = self._reverse_move(move1)
        move5 = self.init_invoice("out_invoice", self.partner_a, "2024-01-02", amounts=[1000], post=True)

        move6 = self._reverse_move(move2)
        move7 = self._reverse_move(move3)

        self._verify_integrity(move1, "Entries are correctly hashed", move1, move3)

        for move in (move4, move6, move7):
            self.assertFalse(move.inalterable_hash)

        self._send(move7)  # Shouldn't raise, no sequence hole if we have a mix of invoices and credit notes
        self.assertFalse(move5.inalterable_hash)  # move5 has another sequence_prefix, so not hashed here
        for move in (move4, move6, move7):
            self.assertNotEqual(move.inalterable_hash, False)

        move8 = self.init_invoice("out_invoice", self.partner_a, "2024-01-02", amounts=[1000], post=True)
        move8.button_hash()  # Hashes move5 too
        for move in (move5 | move8):
            self.assertNotEqual(move.inalterable_hash, False)

        moves = (move1 | move2 | move3 | move4 | move5 | move6 | move7 | move8)
        self._verify_integrity(moves, "Entries are correctly hashed", move1, move8, prefix='INV/')
        self._verify_integrity(moves, "Entries are correctly hashed", move4, move7, prefix='RINV/')

    def test_retroactive_hash_vendor_bills(self):
        """The hash should be retroactive even to vendor bills that were created before the restrict mode was activated."""
        move1 = self.init_invoice("in_invoice", self.partner_a, "2024-01-01", amounts=[1000], post=True)

        self.company_data['default_journal_purchase'].restrict_mode_hash_table = True

        move2 = self.init_invoice("in_invoice", self.partner_a, "2024-01-02", amounts=[1000], post=True)
        self._send(move2)

        # We should hash vendor bills only manually (not on post, nor on Send&Print)
        self.assertFalse(move1.inalterable_hash)
        self.assertFalse(move2.inalterable_hash)

        move2.button_hash()
        self.assertNotEqual(move1.inalterable_hash, False)
        self.assertNotEqual(move2.inalterable_hash, False)
        self._verify_integrity(move1 | move2, "Entries are correctly hashed", move1, move2)

    def test_retroactive_hash_multiple_journals(self):
        """If we have a recordset of moves in different journals, all of them should be hashed
           in a way that respects the journal to which they belong"""
        journal_sale2 = self.env['account.journal'].create({
            'name': 'Sale Journal 2',
            'type': 'sale',
            'code': 'SJ2',
            'company_id': self.company_data['company'].id,
            'restrict_mode_hash_table': True,
        })
        self.company_data['default_journal_sale'].restrict_mode_hash_table = True
        move1 = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'journal_id': journal_sale2.id,
            'partner_id': self.partner_a.id,
            'date': '2024-01-01',
            'invoice_line_ids': [Command.create({
                'name': 'test',
                'quantity': 1,
                'price_unit': 1000,
                'account_id': self.company_data['default_account_revenue'].id,
            })],
        })
        move1.action_post()
        self.assertFalse(move1.inalterable_hash)

        move2 = self.init_invoice("out_invoice", self.partner_a, "2024-01-01", amounts=[1000], post=True)
        self.assertFalse(move2.inalterable_hash)

        move3 = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'journal_id': journal_sale2.id,
            'partner_id': self.partner_a.id,
            'date': '2024-01-01',
            'invoice_line_ids': [Command.create({
                'name': 'test',
                'quantity': 1,
                'price_unit': 1000,
                'account_id': self.company_data['default_account_revenue'].id,
            })],
        })
        move3.action_post()
        self.assertFalse(move3.inalterable_hash)

        move4 = self.init_invoice("out_invoice", self.partner_a, "2024-01-01", amounts=[1000], post=True)
        self.assertFalse(move4.inalterable_hash)

        moves = move1 | move2 | move3 | move4
        moves.button_hash()

        for move in moves:
            self.assertNotEqual(move.inalterable_hash, False)

        self._verify_integrity(moves, "Entries are correctly hashed", move1, move3, prefix=move1.sequence_prefix)
        self._verify_integrity(moves, "Entries are correctly hashed", move2, move4, prefix=move2.sequence_prefix)

    def test_hash_multiyear(self):
        """Test that we can hash entries from different fiscal years"""
        self.company_data['default_journal_sale'].restrict_mode_hash_table = True
        move1 = self.init_invoice("out_invoice", self.partner_a, "2023-01-01", amounts=[1000], post=True)
        move2 = self.init_invoice("out_invoice", self.partner_a, "2023-01-03", amounts=[1000], post=True)
        move3 = self.init_invoice("out_invoice", self.partner_a, "2023-01-02", amounts=[1000], post=True)

        move4 = self.init_invoice("out_invoice", self.partner_a, "2024-01-01", amounts=[1000], post=True)
        move5 = self.init_invoice("out_invoice", self.partner_a, "2024-01-03", amounts=[1000], post=True)
        move6 = self.init_invoice("out_invoice", self.partner_a, "2024-01-04", amounts=[1000], post=True)

        moves = move1 | move2 | move3 | move4 | move5 | move6
        moves.button_hash()

        for move in moves:
            self.assertNotEqual(move.inalterable_hash, False)

        self._verify_integrity(moves, "Entries are correctly hashed", move1, move3, prefix=move1.sequence_prefix)
        self._verify_integrity(moves, "Entries are correctly hashed", move4, move6, prefix=move4.sequence_prefix)

    def test_hash_on_lock_date(self):
        """When setting a lock date, we should hash the moves before the lock date
        otherwise we won't ever be able to hash them"""
        self.company_data['default_journal_sale'].restrict_mode_hash_table = True
        move1 = self.init_invoice("out_invoice", self.partner_a, "2024-01-01", amounts=[1000], post=True)
        move2 = self.init_invoice("out_invoice", self.partner_a, "2024-01-02", amounts=[1000], post=True)
        move3 = self.init_invoice("out_invoice", self.partner_a, "2024-01-03", amounts=[1000], post=True)
        move4 = self.init_invoice("out_invoice", self.partner_a, "2024-02-01", amounts=[1000], post=True)
        move5 = self.init_invoice("out_invoice", self.partner_a, "2024-02-01", amounts=[1000], post=True)

        for move in (move1, move2, move3, move4, move5):
            self.assertFalse(move.inalterable_hash)

        # Shouldn't raise since no moves has ever been hashed
        self.company_data['company'].fiscalyear_lock_date = fields.Date.to_date('2024-01-31')

        # Let's has just one and revert the lock date
        def _autorise_lock_date_changes(*args, **kwargs):
            pass

        with patch('odoo.addons.account_lock.models.res_company.ResCompany._autorise_lock_date_changes', new=_autorise_lock_date_changes):
            self.company_data['company'].fiscalyear_lock_date = False
        move1.button_hash()

        # Now we should raise because we have a hashed move before the lock date
        try:
            self.company_data['company'].fiscalyear_lock_date = fields.Date.to_date('2024-01-31')
        except RedirectWarning as rw:
            self.assertEqual(rw.args[0], 'Some journal entries have not been hashed yet. You should hash them before locking the fiscal year.')
            self.assertEqual(rw.args[1]['domain'][0][2], [move2.id, move3.id])
        else:
            self.fail("RedirectWarning not raised")

        for move in (move2, move3, move4, move5):
            self.assertFalse(move.inalterable_hash)

        # Let's hash them manually
        move5.button_hash()
        for move in (move1, move2, move3, move4, move5):
            self.assertNotEqual(move.inalterable_hash, False)
        self._verify_integrity(move5, "Entries are correctly hashed", move1, move5)

        # Now we can lock
        self.company_data['company'].fiscalyear_lock_date = fields.Date.to_date('2024-01-31')

        # No moves to lock, shouldn't raise
        self.company_data['company'].fiscalyear_lock_date = fields.Date.to_date('2024-02-29')

    def test_retroactive_hashing_before_current(self):
        """Test that we hash entries before the current recordset of moves, not the ons after"""
        self.company_data['default_journal_sale'].restrict_mode_hash_table = True
        move1 = self.init_invoice("out_invoice", self.partner_a, "2024-01-01", amounts=[1000], post=True)
        move2 = self.init_invoice("out_invoice", self.partner_a, "2024-01-02", amounts=[1000], post=True)
        move3 = self.init_invoice("out_invoice", self.partner_a, "2024-01-03", amounts=[1000], post=True)

        move4 = self.init_invoice("out_invoice", self.partner_a, "2024-01-04", amounts=[1000], post=True)
        move5 = self.init_invoice("out_invoice", self.partner_a, "2024-01-05", amounts=[1000], post=True)
        move6 = self.init_invoice("out_invoice", self.partner_a, "2024-01-06", amounts=[1000], post=True)

        move3.button_hash()

        for move in (move1, move2, move3):
            self.assertNotEqual(move.inalterable_hash, False)
        for move in (move4, move5, move6):
            self.assertFalse(move.inalterable_hash)

        self._verify_integrity(move1, "Entries are correctly hashed", move1, move3)
        move6.button_hash()
        self._verify_integrity(move1, "Entries are correctly hashed", move1, move6)

    def test_account_move_hash_versioning_v3_to_v4(self):
        """
        We are updating the hash algorithm. We want to make sure that we do not break the integrity report.
        This test focuses on the case with version 3 and version 4.
        """
        # Let's simulate v3 where the hash was on post and not retroactive
        # First let's create some moves that shouldn't be hashed (before restrict mode)
        secure_sequence = self._get_secure_sequence()
        moves_v3_pre_restrict_mode = self.env['account.move']
        for _ in range(3):
            moves_v3_pre_restrict_mode |= self.init_invoice("out_invoice", self.partner_a, "2024-01-01", amounts=[1000, 2000], post=True)

        self.company_data['default_journal_sale'].restrict_mode_hash_table = True

        # Now create some moves in v3 that should be hashed on post and have a secure_sequence_id
        moves_v3_post_restrict_mode = self.env['account.move']
        last_hash = ""
        for _ in range(3):
            move = self.init_invoice("out_invoice", self.partner_a, "2024-01-01", amounts=[1000, 2000], post=True)
            move.inalterable_hash = move.with_context(hash_version=3)._calculate_hashes(last_hash)[move]
            last_hash = move.inalterable_hash
            move.secure_sequence_number = secure_sequence.next_by_id()
            moves_v3_post_restrict_mode |= move

        moves_v3 = moves_v3_pre_restrict_mode | moves_v3_post_restrict_mode

        # Use v4 now
        moves_v4 = self._init_and_send([
            {'partner': self.partner_a, 'date': '2024-01-02', 'amounts': [1000, 2000]},
            {'partner': self.partner_b, 'date': '2024-01-01', 'amounts': [1000, 2000]},
            {'partner': self.partner_b, 'date': '2024-01-03', 'amounts': [1000, 2000]},
        ])  # Default hash version is 4

        # Don't ever allow to hash moves_v3_pre_restrict_mode
        self._send(moves_v3_pre_restrict_mode[-1])  # Shouldn't raise
        self.assertFalse(moves_v3_pre_restrict_mode[-1].inalterable_hash)

        with self.assertRaisesRegex(UserError, "This move could not be locked either because.*"), self.env.cr.savepoint():
            moves_v3_pre_restrict_mode.button_hash()

        # Test that we allow holes that are not in the moves_to_hash and
        moves_v3_pre_restrict_mode[2].button_draft()  # Create hole in sequence
        moves_v4 |= self.init_invoice("out_invoice", self.partner_a, "2024-01-01", amounts=[1000, 2000], post=True)
        moves_v4[-1].button_hash()
        moves_v3_pre_restrict_mode[2].action_post()  # Revert

        # Check lock date, shouldn't raise even if there are no documents to hash
        self.company_data['company'].fiscalyear_lock_date = fields.Date.to_date('2024-01-31')

        # We should have something like (mix of v3 and v4):
        # Name          | Secure Sequence Number    | Inalterable Hash
        # --------------|---------------------------|------------------
        # ### V3: Restricted mode not activated yet
        # INV/2024/1    |           0               | False
        # INV/2024/2    |           0               | False
        # INV/2024/3    |           0               | False
        # ### V3: Restricted mode activated + hash on post
        # INV/2024/4    |           1               | 87ba4c8...
        # INV/2024/5    |           2               | 09al8if...
        # INV/2024/6    |           3               | 0a9f8a9...
        # ### V4: No secure_sequence_number, hash retroactively on send&print
        # INV/2024/7    |           0               | $4$aj98na1...
        # INV/2024/8    |           0               | $4$9177iai...
        # INV/2024/9    |           0               | $4$nwy7ao9
        # ### INV/2024/1, INV/2024/2, INV/2024/3 should not be hashed

        for move in moves_v3_pre_restrict_mode:
            self.assertFalse(move.inalterable_hash)
            self.assertFalse(move.secure_sequence_number)

        for move in moves_v3_post_restrict_mode:
            self.assertNotEqual(move.inalterable_hash, False)
            self.assertNotEqual(move.secure_sequence_number, False)

        for move in moves_v4:
            self.assertNotEqual(move.inalterable_hash, False)
            self.assertFalse(move.secure_sequence_number)

        moves = moves_v3 | moves_v4

        self._verify_integrity(moves, "Entries are correctly hashed", moves_v3_post_restrict_mode[0], moves[-1], prefix=moves[0].sequence_prefix)

        Model.write(moves_v3_post_restrict_mode[1], {'date': fields.Date.from_string('2024-11-07')})
        self._verify_integrity(moves, f'Corrupted data on journal entry with id {moves_v3_post_restrict_mode[1].id}.*', prefix=moves[0].sequence_prefix)
