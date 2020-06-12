# -*- coding: utf-8 -*-
from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.tests.common import Form
from odoo.tests import tagged
from odoo.exceptions import ValidationError
from odoo import fields

from functools import reduce
import json


@tagged('post_install', '-at_install')
class TestAccountMoveJournalSequencing(AccountTestInvoicingCommon):

    @classmethod
    def setUpClass(cls, chart_template_ref=None):
        super().setUpClass(chart_template_ref=chart_template_ref)

        tax_repartition_line = cls.company_data['default_tax_sale'].invoice_repartition_line_ids\
            .filtered(lambda line: line.repartition_type == 'tax')
        cls.test_move = cls.env['account.move'].create({
            'move_type': 'entry',
            'date': '2016-01-01',
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

    def test_sequence_change_date(self):
        # Check setup
        self.assertEqual(self.test_move.state, 'draft')
        self.assertEqual(self.test_move.name, 'MISC/2016/01/0001')
        self.assertEqual(fields.Date.to_string(self.test_move.date), '2016-01-01')

        # Never posted, the number must change if we change the date
        self.test_move.date = '2020-02-02'
        self.assertEqual(self.test_move.name, 'MISC/2020/02/0001')

        # We don't recompute user's input when posting
        self.test_move.name = 'MyMISC/2020/0000001'
        self.test_move.action_post()
        self.assertEqual(self.test_move.name, 'MyMISC/2020/0000001')

        # Has been posted, and it doesn't change anymore
        self.test_move.button_draft()
        self.test_move.date = '2020-01-02'
        self.test_move.action_post()
        self.assertEqual(self.test_move.name, 'MyMISC/2020/0000001')

    def test_journal_sequence(self):
        self.assertEqual(self.test_move.name, 'MISC/2016/01/0001')
        self.test_move.action_post()
        self.assertEqual(self.test_move.name, 'MISC/2016/01/0001')

        copy1 = self.test_move.copy({'date': '2016-01-01'})
        self.assertEqual(copy1.name, '/')
        copy1.action_post()
        self.assertEqual(copy1.name, 'MISC/2016/01/0002')

        copy2 = self.test_move.copy({'date': '2016-01-01'})
        new_journal = self.test_move.journal_id.copy()
        new_journal.code = "MISC2"
        copy2.journal_id = new_journal
        self.assertEqual(copy2.name, 'MISC2/2016/01/0001')
        with Form(copy2) as move_form:  # It is editable in the form
            move_form.name = 'MyMISC/2099/0001'
        copy2.action_post()
        self.assertEqual(copy2.name, 'MyMISC/2099/0001')

        copy3 = copy2.copy({'date': copy2.date})
        self.assertEqual(copy3.name, '/')
        with self.assertRaises(AssertionError):
            with Form(copy2) as move_form:  # It is not editable in the form
                move_form.name = 'MyMISC/2099/0002'
        copy3.action_post()
        self.assertEqual(copy3.name, 'MyMISC/2099/0002')
        copy3.name = 'MISC2/2016/00002'

        copy4 = copy2.copy({'date': copy2.date})
        copy4.action_post()
        self.assertEqual(copy4.name, 'MISC2/2016/00003')

        copy5 = copy2.copy({'date': copy2.date})
        copy5.date = '2021-02-02'
        copy5.action_post()
        self.assertEqual(copy5.name, 'MISC2/2021/00001')
        copy5.name = 'N\'importe quoi?'

        copy6 = copy5.copy({'date': copy5.date})
        copy6.action_post()
        self.assertEqual(copy6.name, 'N\'importe quoi?1')

    def test_journal_sequence_format(self):
        """Test different format of sequences and what it becomes on another period"""
        sequences = [
            ('JRNL/2016/00001', 'JRNL/2016/00002', 'JRNL/2016/00003', 'JRNL/2017/00001'),
            ('1234567', '1234568', '1234569', '1234570'),
            ('20190910', '20190911', '20190912', '20190913'),
            ('2019-0910', '2019-0911', '2019-0912', '2017-0001'),
            ('201909-10', '201909-11', '201604-01', '201703-01'),
            ('20-10-10', '20-10-11', '16-04-01', '17-03-01'),
            ('2010-10', '2010-11', '2010-12', '2017-01'),
            ('JRNL/2016/00001suffix', 'JRNL/2016/00002suffix', 'JRNL/2016/00003suffix', 'JRNL/2017/00001suffix'),
        ]
        other_moves = self.env['account.move'].search([('journal_id', '=', self.test_move.journal_id.id)]) - self.test_move
        other_moves.unlink()  # Do not interfere when trying to get the highest name for new periods

        init_move = self.test_move
        next_move = init_move.copy()
        next_move_month = init_move.copy()
        next_move_year = init_move.copy()
        init_move.date = '2016-03-12'
        next_move.date = '2016-03-12'
        next_move_month.date = '2016-04-12'
        next_move_year.date = '2017-03-12'
        next_moves = (next_move + next_move_month + next_move_year)
        next_moves.action_post()

        for sequence_init, sequence_next, sequence_next_month, sequence_next_year in sequences:
            init_move.name = sequence_init
            next_moves.name = False
            next_moves._compute_name()
            self.assertRecordValues(next_move + next_move_month + next_move_year, [
                {'name': sequence_next},
                {'name': sequence_next_month},
                {'name': sequence_next_year},
            ])

    def test_journal_next_sequence(self):
        prefix = "TEST_ORDER/2016/"
        self.test_move.name = f"{prefix}1"
        for c in range(2, 25):
            copy = self.test_move.copy({'date': '2016-01-01'})
            copy.name = "/"
            copy.action_post()
            self.assertEqual(copy.name, f"{prefix}{c}")

    def test_journal_sequence_multiple_type(self):
        default_vals = {'name': False, 'date': '2016-01-01'}
        entries = self.env['account.move'].create([{
            **default_vals,
            'line_ids': [
                (0, 0, {'name': 'line', 'account_id': self.company_data['default_account_revenue'].id, 'debit': 50.0, 'credit': 0.0}),
                (0, 0, {'name': 'line', 'account_id': self.company_data['default_account_revenue'].id, 'debit': 0.0, 'credit': 50.0}),
             ]
        } for i in range(2)])
        invoices = self.env['account.move'].create([{
            **default_vals,
            'invoice_date': default_vals['date'],
            'partner_id': self.partner_a.id,
            'move_type': 'out_invoice',
            'invoice_line_ids': [
                (0, 0, {'product_id': self.product_a.id}),
             ]
        } for i in range(2)])
        refunds = self.env['account.move'].create([{
            **default_vals,
            'invoice_date': default_vals['date'],
            'partner_id': self.partner_a.id,
            'move_type': 'out_refund',
            'invoice_line_ids': [
                (0, 0, {'product_id': self.product_a.id}),
             ]
        } for i in range(2)])

        all_moves = entries + invoices + refunds
        all_moves.action_post()
        self.assertRecordValues(all_moves, [
            {'name': 'MISC/2016/01/0002'},
            {'name': 'MISC/2016/01/0003'},
            {'name': 'INV/2016/01/0001'},
            {'name': 'INV/2016/01/0002'},
            {'name': 'RINV/2016/01/0001'},
            {'name': 'RINV/2016/01/0002'},
        ])

    def test_journal_override_sequence_regex(self):
        other_moves = self.env['account.move'].search([('journal_id', '=', self.test_move.journal_id.id)]) - self.test_move
        other_moves.unlink()  # Do not interfere when trying to get the highest name for new periods
        self.test_move.name = '00000876-G 0002/2020'
        next = self.test_move.copy({'date': '2016-01-01'})
        next.action_post()
        self.assertEqual(next.name, '00000876-G 0002/2021')  # Wait, I didn't want this!

        next.journal_id.sequence_override_regex = r'^(?P<seq>\d*)(?P<suffix1>.*?)(?P<year>(\d{4})?)(?P<suffix2>)$'
        next.name = '/'
        next._compute_name()
        self.assertEqual(next.name, '00000877-G 0002/2020')  # Pfew, better!

        next = next = self.test_move.copy({'date': '2016-01-01'})
        next.date = "2017-05-02"
        next.action_post()
        self.assertEqual(next.name, '00000001-G 0002/2017')

    def test_journal_sequence_ordering(self):
        self.test_move.name = 'XMISC/2016/00001'
        copies = reduce((lambda x, y: x+y), [self.test_move.copy() for i in range(6)])

        copies[0].date = '2019-03-05'
        copies[1].date = '2019-03-06'
        copies[2].date = '2019-03-07'
        copies[3].date = '2019-03-04'
        copies[4].date = '2019-03-05'
        copies[5].date = '2019-03-05'
        # that entry is actualy the first one of the period, so it already has a name
        # set it to '/' so that it is recomputed at post to be ordered correctly.
        copies[0].name = '/'
        copies.action_post()

        # Ordered by date
        self.assertEqual(copies[0].name, 'XMISC/2019/00002')
        self.assertEqual(copies[1].name, 'XMISC/2019/00005')
        self.assertEqual(copies[2].name, 'XMISC/2019/00006')
        self.assertEqual(copies[3].name, 'XMISC/2019/00001')
        self.assertEqual(copies[4].name, 'XMISC/2019/00003')
        self.assertEqual(copies[5].name, 'XMISC/2019/00004')

        # Can't have twice the same name
        with self.assertRaises(ValidationError):
            copies[0].name = 'XMISC/2019/00001'

        # Lets remove the order by date
        copies[0].name = 'XMISC/2019/10001'
        copies[1].name = 'XMISC/2019/10002'
        copies[2].name = 'XMISC/2019/10003'
        copies[3].name = 'XMISC/2019/10004'
        copies[4].name = 'XMISC/2019/10005'
        copies[5].name = 'XMISC/2019/10006'

        copies[4].button_draft()
        copies[4].with_context(force_delete=True).unlink()
        copies[5].button_draft()

        wizard = Form(self.env['account.resequence.wizard'].with_context(active_ids=set(copies.ids) - set(copies[4].ids), active_model='account.move'))

        new_values = json.loads(wizard.new_values)
        self.assertEqual(new_values[str(copies[0].id)]['new_by_date'], 'XMISC/2019/10002')
        self.assertEqual(new_values[str(copies[0].id)]['new_by_name'], 'XMISC/2019/10001')

        self.assertEqual(new_values[str(copies[1].id)]['new_by_date'], 'XMISC/2019/10004')
        self.assertEqual(new_values[str(copies[1].id)]['new_by_name'], 'XMISC/2019/10002')

        self.assertEqual(new_values[str(copies[2].id)]['new_by_date'], 'XMISC/2019/10005')
        self.assertEqual(new_values[str(copies[2].id)]['new_by_name'], 'XMISC/2019/10003')

        self.assertEqual(new_values[str(copies[3].id)]['new_by_date'], 'XMISC/2019/10001')
        self.assertEqual(new_values[str(copies[3].id)]['new_by_name'], 'XMISC/2019/10004')

        self.assertEqual(new_values[str(copies[5].id)]['new_by_date'], 'XMISC/2019/10003')
        self.assertEqual(new_values[str(copies[5].id)]['new_by_name'], 'XMISC/2019/10005')

        wizard.save().resequence()

        self.assertEqual(copies[3].state, 'posted')
        self.assertEqual(copies[5].name, 'XMISC/2019/10005')
        self.assertEqual(copies[5].state, 'draft')
