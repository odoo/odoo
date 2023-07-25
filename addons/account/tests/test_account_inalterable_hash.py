from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.models import Model
from odoo.tests import tagged
from odoo import fields
from odoo.exceptions import UserError
from odoo.tools import format_date


@tagged('post_install', '-at_install')
class TestAccountMoveInalterableHash(AccountTestInvoicingCommon):
    @classmethod
    def setUpClass(cls, chart_template_ref=None):
        super().setUpClass(chart_template_ref=chart_template_ref)

    def test_account_move_inalterable_hash(self):
        """Test that we cannot alter a field used for the computation of the inalterable hash"""
        self.company_data['default_journal_sale'].restrict_mode_hash_table = True
        move = self.init_invoice("out_invoice", self.partner_a, "2023-01-01", amounts=[1000], post=True)

        with self.assertRaisesRegex(UserError, "You cannot overwrite the values ensuring the inalterability of the accounting."):
            move.inalterable_hash = 'fake_hash'
        with self.assertRaisesRegex(UserError, "You cannot overwrite the values ensuring the inalterability of the accounting."):
            move.secure_sequence_number = 666
        with self.assertRaisesRegex(UserError, "You cannot edit the following fields due to restrict mode being activated.*"):
            move.name = "fake name"
        with self.assertRaisesRegex(UserError, "You cannot edit the following fields due to restrict mode being activated.*"):
            move.date = fields.Date.from_string('2023-01-02')
        with self.assertRaisesRegex(UserError, "You cannot edit the following fields due to restrict mode being activated.*"):
            move.company_id = 666
        with self.assertRaisesRegex(UserError, "You cannot edit the following fields due to restrict mode being activated.*"):
            move.write({
                'company_id': 666,
                'date': fields.Date.from_string('2023-01-03')
            })

        with self.assertRaisesRegex(UserError, "You cannot edit the following fields.*Account.*"):
            move.line_ids[0].account_id = move.line_ids[1]['account_id']
        with self.assertRaisesRegex(UserError, "You cannot edit the following fields.*Partner.*"):
            move.line_ids[0].partner_id = 666

        # The following fields are not part of the hash so they can be modified
        move.invoice_date_due = fields.Date.from_string('2023-01-02')
        move.line_ids[0].date_maturity = fields.Date.from_string('2023-01-02')

    def test_account_move_hash_integrity_report(self):
        """Test the hash integrity report"""
        moves = (
            self.init_invoice("out_invoice", self.partner_a, "2023-01-01", amounts=[1000, 2000])
            | self.init_invoice("out_invoice", self.partner_b, "2023-01-02", amounts=[1000, 2000])
        )
        moves.action_post()

        # No records to be hashed because the restrict mode is not activated yet
        integrity_check = moves.company_id._check_hash_integrity()['results'][0]  # First journal
        self.assertEqual(integrity_check['msg_cover'], 'This journal is not in strict mode.')

        # No records to be hashed even if the restrict mode is activated because the hashing is not retroactive
        self.company_data['default_journal_sale'].restrict_mode_hash_table = True
        integrity_check = moves.company_id._check_hash_integrity()['results'][0]
        self.assertEqual(integrity_check['msg_cover'], 'There isn\'t any journal entry flagged for data inalterability yet for this journal.')

        # Everything should be correctly hashed and verified
        new_moves = (
            self.init_invoice("out_invoice", self.partner_a, "2023-01-03", amounts=[1000, 2000])
            | self.init_invoice("out_invoice", self.partner_b, "2023-01-04", amounts=[1000, 2000])
            | self.init_invoice("out_invoice", self.partner_a, "2023-01-05", amounts=[1000, 2000])
            | self.init_invoice("out_invoice", self.partner_b, "2023-01-06", amounts=[1000, 2000])
            | self.init_invoice("out_invoice", self.partner_a, "2023-01-07", amounts=[1000, 2000])
        )
        new_moves.action_post()
        moves |= new_moves
        integrity_check = moves.company_id._check_hash_integrity()['results'][0]
        self.assertRegex(integrity_check['msg_cover'], f'Entries are hashed from {moves[2].name}.*')
        self.assertEqual(integrity_check['first_move_date'], format_date(self.env, fields.Date.to_string(moves[2].date)))
        self.assertEqual(integrity_check['last_move_date'], format_date(self.env, fields.Date.to_string(moves[-1].date)))

        # Let's change one of the fields used by the hash. It should be detected by the integrity report.
        # We need to bypass the write method of account.move to do so.
        Model.write(moves[4], {'date': fields.Date.from_string('2023-01-07')})
        integrity_check = moves.company_id._check_hash_integrity()['results'][0]
        self.assertEqual(integrity_check['msg_cover'], f'Corrupted data on journal entry with id {moves[4].id}.')

        # Let's try with the one of the subfields
        Model.write(moves[4], {'date': fields.Date.from_string("2023-01-05")})  # Revert the previous change
        Model.write(moves[-1].line_ids[0], {'partner_id': self.partner_b.id})
        integrity_check = moves.company_id._check_hash_integrity()['results'][0]
        self.assertEqual(integrity_check['msg_cover'], f'Corrupted data on journal entry with id {moves[-1].id}.')

        # Let's try with the inalterable_hash field itself
        Model.write(moves[-1].line_ids[0], {'partner_id': self.partner_a.id})  # Revert the previous change
        Model.write(moves[-1], {'inalterable_hash': 'fake_hash'})
        integrity_check = moves.company_id._check_hash_integrity()['results'][0]
        self.assertEqual(integrity_check['msg_cover'], f'Corrupted data on journal entry with id {moves[-1].id}.')

    def test_account_move_hash_versioning_1(self):
        """We are updating the hash algorithm. We want to make sure that we do not break the integrity report.
        This test focuses on the case where the user has only moves with the old hash algorithm."""
        self.init_invoice("out_invoice", self.partner_a, "2023-01-01", amounts=[1000, 2000], post=True)  # Not hashed
        self.company_data['default_journal_sale'].restrict_mode_hash_table = True
        moves = (
            self.init_invoice("out_invoice", self.partner_a, "2023-01-02", amounts=[1000, 2000])
            | self.init_invoice("out_invoice", self.partner_b, "2023-01-03", amounts=[1000, 2000])
            | self.init_invoice("out_invoice", self.partner_b, "2023-01-04", amounts=[1000, 2000])
        )
        moves.with_context(hash_version=1).action_post()
        integrity_check = moves.company_id._check_hash_integrity()['results'][0]
        self.assertRegex(integrity_check['msg_cover'], f'Entries are hashed from {moves[0].name}.*')
        self.assertEqual(integrity_check['first_move_date'], format_date(self.env, fields.Date.to_string(moves[0].date)))
        self.assertEqual(integrity_check['last_move_date'], format_date(self.env, fields.Date.to_string(moves[-1].date)))

        # Let's change one of the fields used by the hash. It should be detected by the integrity report
        # independently of the hash version used. I.e. we first try the v1 hash, then the v2 hash and neither should work.
        # We need to bypass the write method of account.move to do so.
        Model.write(moves[1], {'date': fields.Date.from_string('2023-01-07')})
        integrity_check = moves.company_id._check_hash_integrity()['results'][0]
        self.assertEqual(integrity_check['msg_cover'], f'Corrupted data on journal entry with id {moves[1].id}.')

    def test_account_move_hash_versioning_2(self):
        """We are updating the hash algorithm. We want to make sure that we do not break the integrity report.
        This test focuses on the case where the user has only moves with the new hash algorithm."""
        self.init_invoice("out_invoice", self.partner_a, "2023-01-01", amounts=[1000, 2000], post=True)  # Not hashed
        self.company_data['default_journal_sale'].restrict_mode_hash_table = True
        moves = (
            self.init_invoice("out_invoice", self.partner_a, "2023-01-01", amounts=[1000, 2000])
            | self.init_invoice("out_invoice", self.partner_b, "2023-01-02", amounts=[1000, 2000])
            | self.init_invoice("out_invoice", self.partner_b, "2023-01-03", amounts=[1000, 2000])
        )
        moves.action_post()
        integrity_check = moves.company_id._check_hash_integrity()['results'][0]
        self.assertRegex(integrity_check['msg_cover'], f'Entries are hashed from {moves[0].name}.*')
        self.assertEqual(integrity_check['first_move_date'], format_date(self.env, fields.Date.to_string(moves[0].date)))
        self.assertEqual(integrity_check['last_move_date'], format_date(self.env, fields.Date.to_string(moves[-1].date)))

        # Let's change one of the fields used by the hash. It should be detected by the integrity report
        # independently of the hash version used. I.e. we first try the v1 hash, then the v2 hash and neither should work.
        # We need to bypass the write method of account.move to do so.
        Model.write(moves[1], {'date': fields.Date.from_string('2023-01-07')})
        integrity_check = moves.company_id._check_hash_integrity()['results'][0]
        self.assertEqual(integrity_check['msg_cover'], f'Corrupted data on journal entry with id {moves[1].id}.')

    def test_account_move_hash_versioning_v1_to_v2(self):
        """We are updating the hash algorithm. We want to make sure that we do not break the integrity report.
        This test focuses on the case where the user has moves with both hash algorithms."""
        self.init_invoice("out_invoice", self.partner_a, "2023-01-01", amounts=[1000, 2000], post=True)  # Not hashed
        self.company_data['default_journal_sale'].restrict_mode_hash_table = True
        moves_v1 = (
            self.init_invoice("out_invoice", self.partner_a, "2023-01-01", amounts=[1000, 2000])
            | self.init_invoice("out_invoice", self.partner_b, "2023-01-02", amounts=[1000, 2000])
            | self.init_invoice("out_invoice", self.partner_b, "2023-01-03", amounts=[1000, 2000])
        )
        moves_v1.with_context(hash_version=1).action_post()
        fields_v1 = moves_v1.with_context(hash_version=1)._get_integrity_hash_fields()
        moves_v2 = (
            self.init_invoice("out_invoice", self.partner_a, "2023-01-01", amounts=[1000, 2000])
            | self.init_invoice("out_invoice", self.partner_b, "2023-01-02", amounts=[1000, 2000])
            | self.init_invoice("out_invoice", self.partner_b, "2023-01-03", amounts=[1000, 2000])
        )
        moves_v2.with_context(hash_version=2).action_post()
        fields_v2 = moves_v2._get_integrity_hash_fields()
        self.assertNotEqual(fields_v1, fields_v2)  # Make sure two different hash algorithms were used

        moves = moves_v1 | moves_v2
        integrity_check = moves.company_id._check_hash_integrity()['results'][0]
        self.assertRegex(integrity_check['msg_cover'], f'Entries are hashed from {moves[0].name}.*')
        self.assertEqual(integrity_check['first_move_date'], format_date(self.env, fields.Date.to_string(moves[0].date)))
        self.assertEqual(integrity_check['last_move_date'], format_date(self.env, fields.Date.to_string(moves[-1].date)))

        # Let's change one of the fields used by the hash. It should be detected by the integrity report
        # independently of the hash version used. I.e. we first try the v1 hash, then the v2 hash and neither should work.
        # We need to bypass the write method of account.move to do so.
        Model.write(moves[4], {'date': fields.Date.from_string('2023-01-07')})
        integrity_check = moves.company_id._check_hash_integrity()['results'][0]
        self.assertEqual(integrity_check['msg_cover'], f'Corrupted data on journal entry with id {moves[4].id}.')

        # Let's revert the change and make sure that we cannot use the v1 after the v2.
        # This means we don't simply check whether the move is correctly hashed with either algorithms,
        # but that we can only use v2 after v1 and not go back to v1 afterwards.
        Model.write(moves[4], {'date': fields.Date.from_string("2023-01-02")})  # Revert the previous change
        moves_v1_bis = (
            self.init_invoice("out_invoice", self.partner_a, "2023-01-10", amounts=[1000, 2000])
            | self.init_invoice("out_invoice", self.partner_b, "2023-01-11", amounts=[1000, 2000])
            | self.init_invoice("out_invoice", self.partner_b, "2023-01-12", amounts=[1000, 2000])
        )
        moves_v1_bis.with_context(hash_version=1).action_post()
        integrity_check = moves.company_id._check_hash_integrity()['results'][0]
        self.assertEqual(integrity_check['msg_cover'], f'Corrupted data on journal entry with id {moves_v1_bis[0].id}.')
