# -*- coding: utf-8 -*-
from odoo.addons.account.tests.invoice_test_common import InvoiceTestCommon
from odoo.tests import tagged, new_test_user
from odoo import fields
from odoo.exceptions import ValidationError, UserError


@tagged('post_install', '-at_install')
class TestAccountMove(InvoiceTestCommon):

    @classmethod
    def setUpClass(cls):
        super(TestAccountMove, cls).setUpClass()

        tax_repartition_line = cls.company_data['default_tax_sale'].invoice_repartition_line_ids\
            .filtered(lambda line: line.repartition_type == 'tax')
        cls.test_move = cls.env['account.move'].create({
            'type': 'entry',
            'date': fields.Date.from_string('2016-01-01'),
            'line_ids': [
                (0, None, {
                    'name': 'revenue line 1',
                    'account_id': cls.company_data['default_account_revenue'].id,
                    'debit': 500.0,
                    'credit': 0.0,
                }),
                (0, None, {
                    'name': 'revenue line 2',
                    'account_id': cls.company_data['default_account_revenue'].id,
                    'debit': 1000.0,
                    'credit': 0.0,
                    'tax_ids': [(6, 0, cls.company_data['default_tax_sale'].ids)],
                }),
                (0, None, {
                    'name': 'tax line',
                    'account_id': cls.company_data['default_account_tax_sale'].id,
                    'debit': 150.0,
                    'credit': 0.0,
                    'tax_repartition_line_id': tax_repartition_line.id,
                }),
                (0, None, {
                    'name': 'counterpart line',
                    'account_id': cls.company_data['default_account_expense'].id,
                    'debit': 0.0,
                    'credit': 1650.0,
                }),
            ]
        })

    def test_misc_fiscalyear_lock_date_1(self):
        self.test_move.post()

        # Set the lock date after the journal entry date.
        self.test_move.company_id.fiscalyear_lock_date = fields.Date.from_string('2017-01-01')

        # lines[0] = 'counterpart line'
        # lines[1] = 'tax line'
        # lines[2] = 'revenue line 1'
        # lines[3] = 'revenue line 2'
        lines = self.test_move.line_ids.sorted('debit')

        # Try to edit a line not affecting the taxes.
        with self.assertRaises(UserError), self.cr.savepoint():
            self.test_move.write({
                'line_ids': [
                    (1, lines[0].id, {'credit': lines[0].credit + 100.0}),
                    (1, lines[2].id, {'debit': lines[2].debit + 100.0}),
                ],
            })

        # Try to edit the account of a line.
        with self.assertRaises(UserError), self.cr.savepoint():
            self.test_move.line_ids[0].write({'account_id': self.test_move.line_ids[0].account_id.copy().id})

        # Try to edit a line.
        with self.assertRaises(UserError), self.cr.savepoint():
            self.test_move.write({
                'line_ids': [
                    (1, lines[0].id, {'credit': lines[0].credit + 100.0}),
                    (1, lines[3].id, {'debit': lines[3].debit + 100.0}),
                ],
            })

        # Try to add a new tax on a line.
        with self.assertRaises(UserError), self.cr.savepoint():
            self.test_move.write({
                'line_ids': [
                    (1, lines[2].id, {'tax_ids': [(6, 0, self.company_data['default_tax_purchase'].ids)]}),
                ],
            })

        # Try to create a new line.
        with self.assertRaises(UserError), self.cr.savepoint():
            self.test_move.write({
                'line_ids': [
                    (1, lines[0].id, {'credit': lines[0].credit + 100.0}),
                    (0, None, {
                        'name': 'revenue line 1',
                        'account_id': self.company_data['default_account_revenue'].id,
                        'debit': 100.0,
                        'credit': 0.0,
                    }),
                ],
            })

        # You can't remove the journal entry from a locked period.
        with self.assertRaises(UserError), self.cr.savepoint():
            self.test_move.date = fields.Date.from_string('2018-01-01')

        with self.assertRaises(UserError), self.cr.savepoint():
            self.test_move.unlink()

        with self.assertRaises(UserError), self.cr.savepoint():
            self.test_move.button_draft()

        copy_move = self.test_move.copy()

        # Try to add a new journal entry prior to the lock date.
        with self.assertRaises(UserError), self.cr.savepoint():
            copy_move.post()

        # You can change the date as the journal entry is not posted.
        copy_move.date = fields.Date.from_string('2018-01-01')
        copy_move.post()

        # You can't change the date to one being in a locked period.
        with self.assertRaises(UserError), self.cr.savepoint():
            copy_move.date = fields.Date.from_string('2017-01-01')

    def test_misc_tax_lock_date_1(self):
        self.test_move.post()

        # Set the tax lock date after the journal entry date.
        self.test_move.company_id.tax_lock_date = fields.Date.from_string('2017-01-01')

        # lines[0] = 'counterpart line'
        # lines[1] = 'tax line'
        # lines[2] = 'revenue line 1'
        # lines[3] = 'revenue line 2'
        lines = self.test_move.line_ids.sorted('debit')

        # Try to edit a line not affecting the taxes.
        self.test_move.write({
            'line_ids': [
                (1, lines[0].id, {'credit': lines[0].credit + 100.0}),
                (1, lines[2].id, {'debit': lines[2].debit + 100.0}),
            ],
        })

        # Try to edit the account of a line.
        self.test_move.line_ids[0].write({'account_id': self.test_move.line_ids[0].account_id.copy().id})

        # Try to edit a line having some taxes.
        with self.assertRaises(UserError), self.cr.savepoint():
            self.test_move.write({
                'line_ids': [
                    (1, lines[0].id, {'credit': lines[0].credit + 100.0}),
                    (1, lines[3].id, {'debit': lines[3].debit + 100.0}),
                ],
            })

        # Try to add a new tax on a line.
        with self.assertRaises(UserError), self.cr.savepoint():
            self.test_move.write({
                'line_ids': [
                    (1, lines[2].id, {'tax_ids': [(6, 0, self.company_data['default_tax_purchase'].ids)]}),
                ],
            })

        # Try to edit a tax line.
        with self.assertRaises(UserError), self.cr.savepoint():
            self.test_move.write({
                'line_ids': [
                    (1, lines[0].id, {'credit': lines[0].credit + 100.0}),
                    (1, lines[1].id, {'debit': lines[1].debit + 100.0}),
                ],
            })

        # Try to create a line not affecting the taxes.
        self.test_move.write({
            'line_ids': [
                (1, lines[0].id, {'credit': lines[0].credit + 100.0}),
                (0, None, {
                    'name': 'revenue line 1',
                    'account_id': self.company_data['default_account_revenue'].id,
                    'debit': 100.0,
                    'credit': 0.0,
                }),
            ],
        })

        # Try to create a line affecting the taxes.
        with self.assertRaises(UserError), self.cr.savepoint():
            self.test_move.write({
                'line_ids': [
                    (1, lines[0].id, {'credit': lines[0].credit + 100.0}),
                    (0, None, {
                        'name': 'revenue line 2',
                        'account_id': self.company_data['default_account_revenue'].id,
                        'debit': 1000.0,
                        'credit': 0.0,
                        'tax_ids': [(6, 0, self.company_data['default_tax_sale'].ids)],
                    }),
                ],
            })

        # You can't remove the journal entry from a locked period.
        with self.assertRaises(UserError), self.cr.savepoint():
            self.test_move.date = fields.Date.from_string('2018-01-01')

        with self.assertRaises(UserError), self.cr.savepoint():
            self.test_move.unlink()

        with self.assertRaises(UserError), self.cr.savepoint():
            self.test_move.button_draft()

        copy_move = self.test_move.copy()

        # /!\ The date is changed automatically to the next available one during the post.
        copy_move.post()

        # You can't change the date to one being in a locked period.
        with self.assertRaises(UserError), self.cr.savepoint():
            copy_move.date = fields.Date.from_string('2017-01-01')

    def test_misc_draft_reconciled_entries_1(self):
        draft_moves = self.env['account.move'].create([
            {
                'type': 'entry',
                'line_ids': [
                    (0, None, {
                        'name': 'move 1 receivable line',
                        'account_id': self.company_data['default_account_receivable'].id,
                        'debit': 1000.0,
                        'credit': 0.0,
                    }),
                    (0, None, {
                        'name': 'move 1 counterpart line',
                        'account_id': self.company_data['default_account_expense'].id,
                        'debit': 0.0,
                        'credit': 1000.0,
                    }),
                ]
            },
            {
                'type': 'entry',
                'line_ids': [
                    (0, None, {
                        'name': 'move 2 receivable line',
                        'account_id': self.company_data['default_account_receivable'].id,
                        'debit': 0.0,
                        'credit': 2000.0,
                    }),
                    (0, None, {
                        'name': 'move 2 counterpart line',
                        'account_id': self.company_data['default_account_expense'].id,
                        'debit': 2000.0,
                        'credit': 0.0,
                    }),
                ]
            },
        ])

        # lines[0] = 'move 2 receivable line'
        # lines[1] = 'move 1 counterpart line'
        # lines[2] = 'move 1 receivable line'
        # lines[3] = 'move 2 counterpart line'
        lines = draft_moves.mapped('line_ids').sorted('balance')

        (lines[0] + lines[2]).reconcile()

        draft_moves.flush()
        self.cr.execute('SAVEPOINT test_misc_draft_reconciled_entries_1')

        with self.assertRaises(UserError):
            draft_moves[0].write({
                'line_ids': [
                    (1, lines[1].id, {'credit': lines[1].credit + 100.0}),
                    (1, lines[2].id, {'debit': lines[2].debit + 100.0}),
                ]
            })

        with self.assertRaises(UserError):
            draft_moves.unlink()

        draft_moves.flush()
        draft_moves.invalidate_cache()
        self.cr.execute('ROLLBACK TO SAVEPOINT test_misc_draft_reconciled_entries_1')

    def test_misc_unique_sequence_number(self):
        ''' Ensure two journal entries can't share the same name when using the same sequence. '''
        self.test_move.post()

        # Edit the sequence to force the next move to get the same name.
        self.test_move.journal_id\
            .sequence_id.date_range_ids\
            .filtered(lambda seq: seq.date_from == fields.Date.from_string('2016-01-01')).number_next -= 1

        test_move2 = self.test_move.copy()
        with self.assertRaises(ValidationError):
            test_move2.post()

    def test_add_followers_on_post(self):
        # Add some existing partners, some from another company
        company = self.env['res.company'].create({'name': 'Oopo'})
        existing_partners = self.env['res.partner'].create([{
            'name': 'Jean',
            'company_id': company.id,
        },{
            'name': 'Paulus',
        }])
        self.test_move.message_subscribe(existing_partners.ids)

        user = new_test_user(self.env, login='jag', groups='account.group_account_invoice')

        move = self.test_move.with_user(user)
        partner = self.env['res.partner'].create({'name': 'Belouga'})
        commercial_partner = self.env['res.partner'].create({'name': 'Rorqual'})
        move.partner_id = partner
        move.commercial_partner_id = commercial_partner

        move.post()
        self.assertEqual(move.message_partner_ids, self.env.user.partner_id | existing_partners | partner | commercial_partner)
