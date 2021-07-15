# -*- coding: utf-8 -*-
from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.tests import tagged
from odoo.tests.common import Form
from odoo import fields, api, SUPERUSER_ID
from odoo.exceptions import ValidationError
from odoo.tools import mute_logger

from dateutil.relativedelta import relativedelta
from functools import reduce
import json
import psycopg2


@tagged('post_install', '-at_install')
class TestSequenceMixin(AccountTestInvoicingCommon):

    @classmethod
    def setUpClass(cls, chart_template_ref=None):
        super().setUpClass(chart_template_ref=chart_template_ref)
        cls.test_move = cls.create_move()

    @classmethod
    def create_move(cls, move_type=None, date=None, journal=None, name=None, post=False):
        move = cls.env['account.move'].create({
            'move_type': move_type or 'entry',
            'date': date or '2016-01-01',
            'line_ids': [
                (0, None, {
                    'name': 'line',
                    'account_id': cls.company_data['default_account_revenue'].id,
                }),
            ]
        })
        if journal:
            move.name = False
            move.journal_id = journal
        if name:
            move.name = name
        if post:
            move.action_post()
        return move

    def test_sequence_change_date(self):
        """Change the sequence when we change the date iff it has never been posted."""
        # Check setup
        self.assertEqual(self.test_move.state, 'draft')
        self.assertEqual(self.test_move.name, 'MISC/2016/01/0001')
        self.assertEqual(fields.Date.to_string(self.test_move.date), '2016-01-01')

        # Never posetd, the number must change if we change the date
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

        copy1 = self.create_move(date=self.test_move.date)
        self.assertEqual(copy1.name, '/')
        copy1.action_post()
        self.assertEqual(copy1.name, 'MISC/2016/01/0002')

        copy2 = self.create_move(date=self.test_move.date)
        new_journal = self.test_move.journal_id.copy()
        new_journal.code = "MISC2"
        copy2.journal_id = new_journal
        self.assertEqual(copy2.name, 'MISC2/2016/01/0001')
        with Form(copy2) as move_form:  # It is editable in the form
            move_form.name = 'MyMISC/2016/0001'
            move_form.journal_id = self.test_move.journal_id
            self.assertEqual(move_form.name, '/')
            move_form.journal_id = new_journal
            self.assertEqual(move_form.name, 'MISC2/2016/01/0001')
            move_form.name = 'MyMISC/2016/0001'
        copy2.action_post()
        self.assertEqual(copy2.name, 'MyMISC/2016/0001')

        copy3 = self.create_move(date=copy2.date, journal=new_journal)
        self.assertEqual(copy3.name, '/')
        with self.assertRaises(AssertionError):
            with Form(copy2) as move_form:  # It is not editable in the form
                move_form.name = 'MyMISC/2016/0002'
        copy3.action_post()
        self.assertEqual(copy3.name, 'MyMISC/2016/0002')
        copy3.name = 'MISC2/2016/00002'

        copy4 = self.create_move(date=copy2.date, journal=new_journal)
        copy4.action_post()
        self.assertEqual(copy4.name, 'MISC2/2016/00003')

        copy5 = self.create_move(date=copy2.date, journal=new_journal)
        copy5.date = '2021-02-02'
        copy5.action_post()
        self.assertEqual(copy5.name, 'MISC2/2021/00001')
        copy5.name = 'N\'importe quoi?'

        copy6 = self.create_move(date=copy5.date, journal=new_journal)
        copy6.action_post()
        self.assertEqual(copy6.name, 'N\'importe quoi?1')

    def test_journal_sequence_format(self):
        """Test different format of sequences and what it becomes on another period"""
        sequences = [
            ('JRNL/2016/00001', 'JRNL/2016/00002', 'JRNL/2016/00003', 'JRNL/2017/00001'),
            ('1234567', '1234568', '1234569', '1234570'),
            ('20190910', '20190911', '20190912', '20190913'),
            ('2016-0910', '2016-0911', '2016-0912', '2017-0001'),
            ('201603-10', '201603-11', '201604-01', '201703-01'),
            ('16-03-10', '16-03-11', '16-04-01', '17-03-01'),
            ('2016-10', '2016-11', '2016-12', '2017-01'),
            ('045-001-000002', '045-001-000003', '045-001-000004', '045-001-000005'),
            ('JRNL/2016/00001suffix', 'JRNL/2016/00002suffix', 'JRNL/2016/00003suffix', 'JRNL/2017/00001suffix'),
        ]

        init_move = self.create_move(date='2016-03-12')
        next_move = self.create_move(date='2016-03-12')
        next_move_month = self.create_move(date='2016-04-12')
        next_move_year = self.create_move(date='2017-03-12')
        next_moves = (next_move + next_move_month + next_move_year)
        next_moves.action_post()

        for sequence_init, sequence_next, sequence_next_month, sequence_next_year in sequences:
            init_move.name = sequence_init
            next_moves.name = False
            next_moves._compute_name()
            self.assertEqual(
                [next_move.name, next_move_month.name, next_move_year.name],
                [sequence_next, sequence_next_month, sequence_next_year],
            )

    def test_journal_next_sequence(self):
        """Sequences behave correctly even when there is not enough padding."""
        prefix = "TEST_ORDER/2016/"
        self.test_move.name = f"{prefix}1"
        for c in range(2, 25):
            copy = self.create_move(date=self.test_move.date)
            copy.name = "/"
            copy.action_post()
            self.assertEqual(copy.name, f"{prefix}{c}")

    def test_journal_sequence_multiple_type(self):
        """Domain is computed accordingly to different types."""
        entry, entry2, invoice, invoice2, refund, refund2 = (
            self.create_move(date='2016-01-01')
            for i in range(6)
        )
        (invoice + invoice2 + refund + refund2).write({
            'journal_id': self.company_data['default_journal_sale'],
            'partner_id': 1,
            'invoice_date': '2016-01-01',
        })
        (invoice + invoice2).move_type = 'out_invoice'
        (refund + refund2).move_type = 'out_refund'
        all = (entry + entry2 + invoice + invoice2 + refund + refund2)
        all.name = False
        all.action_post()
        self.assertEqual(entry.name, 'MISC/2016/01/0002')
        self.assertEqual(entry2.name, 'MISC/2016/01/0003')
        self.assertEqual(invoice.name, 'INV/2016/01/0001')
        self.assertEqual(invoice2.name, 'INV/2016/01/0002')
        self.assertEqual(refund.name, 'RINV/2016/01/0001')
        self.assertEqual(refund2.name, 'RINV/2016/01/0002')

    def test_journal_sequence_groupby_compute(self):
        """The grouping optimization is correctly done."""
        # Setup two journals with a sequence that resets yearly
        journals = self.env['account.journal'].create([{
            'name': f'Journal{i}',
            'code': f'J{i}',
            'type': 'general',
        } for i in range(2)])
        account = self.env['account.account'].search([], limit=1)
        moves = self.env['account.move'].create([{
            'journal_id': journals[i].id,
            'line_ids': [(0, 0, {'account_id': account.id, 'name': 'line'})],
            'date': '2010-01-01',
        } for i in range(2)])._post()
        for i in range(2):
            moves[i].name = f'J{i}/2010/00001'

        # Check that the moves are correctly batched
        moves = self.env['account.move'].create([{
            'journal_id': journals[journal_index].id,
            'line_ids': [(0, 0, {'account_id': account.id, 'name': 'line'})],
            'date': f'2010-{month}-01',
        } for journal_index, month in [(1, 1), (0, 1), (1, 2), (1, 1)]])._post()
        self.assertEqual(
            moves.mapped('name'),
            ['J1/2010/00002', 'J0/2010/00002', 'J1/2010/00004', 'J1/2010/00003'],
        )

        journals[0].code = 'OLD'
        journals.flush()
        journal_same_code = self.env['account.journal'].create([{
            'name': 'Journal0',
            'code': 'J0',
            'type': 'general',
        }])
        moves = (
            self.create_move(date='2010-01-01', journal=journal_same_code, name='J0/2010/00001')
            + self.create_move(date='2010-01-01', journal=journal_same_code)
            + self.create_move(date='2010-01-01', journal=journal_same_code)
            + self.create_move(date='2010-01-01', journal=journals[0])
        )._post()
        self.assertEqual(
            moves.mapped('name'),
            ['J0/2010/00001', 'J0/2010/00002', 'J0/2010/00003', 'J0/2010/00003'],
        )

    def test_journal_override_sequence_regex(self):
        """There is a possibility to override the regex and change the order of the paramters."""
        self.create_move(date='2020-01-01', name='00000876-G 0002/2020')
        next = self.create_move(date='2020-01-01')
        next.action_post()
        self.assertEqual(next.name, '00000876-G 0002/2021')  # Wait, I didn't want this!

        next.button_draft()
        next.name = False
        next.journal_id.sequence_override_regex = r'^(?P<seq>\d*)(?P<suffix1>.*?)(?P<year>(\d{4})?)(?P<suffix2>)$'
        next.action_post()
        self.assertEqual(next.name, '00000877-G 0002/2020')  # Pfew, better!
        next = self.create_move(date='2020-01-01')
        next.action_post()
        self.assertEqual(next.name, '00000878-G 0002/2020')

        next = self.create_move(date='2017-05-02')
        next.action_post()
        self.assertEqual(next.name, '00000001-G 0002/2017')

    def test_journal_sequence_ordering(self):
        """Entries are correctly sorted when posting multiple at once."""
        self.test_move.name = 'XMISC/2016/00001'
        copies = reduce((lambda x, y: x+y), [
            self.create_move(date=self.test_move.date)
            for i in range(6)
        ])

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

        wizard = Form(self.env['account.resequence.wizard'].with_context(
            active_ids=set(copies.ids) - set(copies[4].ids),
            active_model='account.move'),
        )

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

    def test_sequence_get_more_specific(self):
        """There is the ability to change the format (i.e. from yearly to montlhy)."""
        def test_date(date, name):
            test = self.create_move(date=date)
            test.action_post()
            self.assertEqual(test.name, name)

        def set_sequence(date, name):
            return self.create_move(date=date, name=name)._post()

        # Start with a continuous sequence
        self.test_move.name = 'MISC/00001'

        # Change the prefix to reset every year starting in 2017
        new_year = set_sequence(self.test_move.date + relativedelta(years=1), 'MISC/2017/00001')

        # Change the prefix to reset every month starting in February 2017
        new_month = set_sequence(new_year.date + relativedelta(months=1), 'MISC/2017/02/00001')

        test_date(self.test_move.date, 'MISC/00002')  # Keep the old prefix in 2016
        test_date(new_year.date, 'MISC/2017/00002')  # Keep the new prefix in 2017
        test_date(new_month.date, 'MISC/2017/02/00002')  # Keep the new prefix in February 2017

        # Change the prefix to never reset (again) year starting in 2018 (Please don't do that)
        reset_never = set_sequence(self.test_move.date + relativedelta(years=2), 'MISC/00100')
        test_date(reset_never.date, 'MISC/00101')  # Keep the new prefix in 2018

    def test_sequence_concurency(self):
        """Computing the same name in concurent transactions is not allowed."""
        with self.env.registry.cursor() as cr0,\
                self.env.registry.cursor() as cr1,\
                self.env.registry.cursor() as cr2:
            env0 = api.Environment(cr0, SUPERUSER_ID, {})
            env1 = api.Environment(cr1, SUPERUSER_ID, {})
            env2 = api.Environment(cr2, SUPERUSER_ID, {})

            journal = env0['account.journal'].create({
                'name': 'concurency_test',
                'code': 'CT',
                'type': 'general',
            })
            account = env0['account.account'].create({
                'code': 'CT',
                'name': 'CT',
                'user_type_id': env0.ref('account.data_account_type_fixed_assets').id,
            })
            moves = env0['account.move'].create([{
                'journal_id': journal.id,
                'date': fields.Date.from_string('2016-01-01'),
                'line_ids': [(0, 0, {'name': 'name', 'account_id': account.id})]
            }] * 3)
            moves.name = '/'
            moves[0].action_post()
            self.assertEqual(moves.mapped('name'), ['CT/2016/01/0001', '/', '/'])
            env0.cr.commit()

            # start the transactions here on cr2 to simulate concurency with cr1
            env2.cr.execute('SELECT 1')

            move = env1['account.move'].browse(moves[1].id)
            move.action_post()
            env1.cr.commit()

            move = env2['account.move'].browse(moves[2].id)
            with self.assertRaises(psycopg2.OperationalError), env2.cr.savepoint(), mute_logger('odoo.sql_db'):
                move.action_post()

            self.assertEqual(moves.mapped('name'), ['CT/2016/01/0001', 'CT/2016/01/0002', '/'])
            moves.button_draft()
            moves.posted_before = False
            moves.unlink()
            journal.unlink()
            account.unlink()
            env0.cr.commit()
