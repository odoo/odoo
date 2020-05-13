# -*- coding: utf-8 -*-
from odoo.addons.account.tests.account_test_classes import AccountingTestCase
from odoo.tests import tagged
from odoo.tests.common import Form


@tagged('post_install', '-at_install')
class TestAccountMoveTaxesEdition(AccountingTestCase):

    def setUp(self):
        super(AccountingTestCase, self).setUp()
        self.percent_tax = self.env['account.tax'].create({
            'name': 'tax_line',
            'amount_type': 'percent',
            'amount': 10,
        })
        self.included_percent_tax = self.env['account.tax'].create({
            'name': 'included_tax_line',
            'amount_type': 'percent',
            'amount': 20,
            'price_include': True,
            'include_base_amount': False,
        })
        self.account = self.env['account.account'].search([('deprecated', '=', False)], limit=1)
        self.journal = self.env['account.journal'].search([], limit=1)

    def test_onchange_taxes_1(self):
        '''
        Test an account.move.line is created automatically when adding a tax.
        This test uses the following scenario:
            - Create manually a debit line of 1000 having a tax.
            - Assume a line containing the tax amount is created automatically.
            - Create manually a credit line to balance the two previous lines.
            - Save the move.

        tax = 10%

        Name            | Debit     | Credit    | Tax_ids       | Tax_line_id's name
        ----------------|-----------|-----------|---------------|-------------------
        debit_line_1    | 1000      |           | tax           |
        tax_line        | 100       |           |               | tax_line
        debit_line_1    |           | 1100      |               |
        '''
        move_form = Form(self.env['account.move'], view='account.view_move_form')
        move_form.ref = 'azerty'
        move_form.journal_id = self.journal

        # Create a new account.move.line with debit amount.
        with move_form.line_ids.new() as debit_line:
            debit_line.name = 'debit_line_1'
            debit_line.account_id = self.account
            debit_line.debit = 1000
            debit_line.tax_ids.clear()
            debit_line.tax_ids.add(self.percent_tax)

            self.assertTrue(debit_line.recompute_tax_line)

        # Create a third account.move.line with credit amount.
        with move_form.line_ids.new() as credit_line:
            credit_line.name = 'credit_line_1'
            credit_line.account_id = self.account
            credit_line.credit = 1100

        move = move_form.save()

        self.assertRecordValues(move.line_ids, [
            {'name': 'credit_line_1',   'debit': 0.0,       'credit': 1100.0,   'tax_ids': [],                      'tax_line_id': False},
            {'name': 'tax_line',        'debit': 100.0,     'credit': 0.0,      'tax_ids': [],                      'tax_line_id': self.percent_tax.id},
            {'name': 'debit_line_1', 'debit': 1000.0, 'credit': 0.0, 'tax_ids': [self.percent_tax.id], 'tax_line_id': False},
        ])

    def test_onchange_taxes_2(self):
        '''
        Test the amount of tax account.move.line is adapted when editing the account.move.line amount.
        This test uses the following scenario:
            - Create manually a debit line of 1000 having a tax.
            - Assume a line containing the tax amount is created automatically.
            - Set the debit amount to 2000 in the first created line.
            - Assume the line containing the tax amount has been updated automatically.
            - Create manually a credit line to balance the two previous lines.
            - Save the move.

        tax = 10%

        Name            | Debit     | Credit    | Tax_ids       | Tax_line_id's name
        ----------------|-----------|-----------|---------------|-------------------
        debit_line_1    | 2000      |           | tax           |
        tax_line        | 200       |           |               | tax_line
        debit_line_1    |           | 2200      |               |
        '''
        move_form = Form(self.env['account.move'], view='account.view_move_form')
        move_form.ref = 'azerty'
        move_form.journal_id = self.journal

        # Create a new account.move.line with debit amount.
        with move_form.line_ids.new() as debit_line:
            debit_line.name = 'debit_line_1'
            debit_line.account_id = self.account
            debit_line.debit = 1000
            debit_line.tax_ids.clear()
            debit_line.tax_ids.add(self.percent_tax)

            self.assertTrue(debit_line.recompute_tax_line)

            debit_line.debit = 2000

            self.assertTrue(debit_line.recompute_tax_line)

        # Create a third account.move.line with credit amount.
        with move_form.line_ids.new() as credit_line:
            credit_line.name = 'credit_line_1'
            credit_line.account_id = self.account
            credit_line.credit = 2200

        move = move_form.save()

        self.assertRecordValues(move.line_ids, [
            {'name': 'credit_line_1',   'debit': 0.0,       'credit': 2200.0,   'tax_ids': [],                      'tax_line_id': False},
            {'name': 'tax_line',        'debit': 200.0,     'credit': 0.0,      'tax_ids': [],                      'tax_line_id': self.percent_tax.id},
            {'name': 'debit_line_1', 'debit': 2000.0, 'credit': 0.0, 'tax_ids': [self.percent_tax.id], 'tax_line_id': False},
        ])

    def test_onchange_taxes_3(self):
        '''
        Test the amount of tax account.move.line is still editable manually.
        Test the amount of tax account.move.line is cumulative for the same tax.
        This test uses the following scenario:
            - Create manually a debit line of 1000 having a tax.
            - Assume a line containing the tax amount is created automatically.
            - Edit the tax line amount of the auto-generated line by adding 5.
            - Create manually a credit line to balance the two previous lines.
            - Save the move.
            - Edit the move.
            - Create manually a debit line of 2000 having the same tax.
            - Assume the line containing the tax amount has been updated (no new line created).
            - Create manually a credit line to balance the four previous lines.
            - Save the move.

        tax = 10%

        Name            | Debit     | Credit    | Tax_ids       | Tax_line_id's name
        ----------------|-----------|-----------|---------------|-------------------
        debit_line_1    | 1000      |           | tax           |
        tax_line        | 300       |           |               | tax_line
        credit_line_1   |           | 1105      |               |
        debit_line_2    | 2000      |           | tax           |
        credit_line_2   |           | 2195      |               |
        '''
        move_form = Form(self.env['account.move'], view='account.view_move_form')
        move_form.ref = 'azerty'
        move_form.journal_id = self.journal

        # Create a new account.move.line with debit amount.
        with move_form.line_ids.new() as debit_line:
            debit_line.name = 'debit_line_1'
            debit_line.account_id = self.account
            debit_line.debit = 1000
            debit_line.tax_ids.clear()
            debit_line.tax_ids.add(self.percent_tax)

            self.assertTrue(debit_line.recompute_tax_line)

        # Edit the tax account.move.line
        with move_form.line_ids.edit(index=1) as tax_line:
            tax_line.debit = 105  # Was 100

        # Create a third account.move.line with credit amount.
        with move_form.line_ids.new() as credit_line:
            credit_line.name = 'credit_line_1'
            credit_line.account_id = self.account
            credit_line.credit = 1105

        move = move_form.save()

        move_form = Form(move, view='account.view_move_form')
        # Create a new account.move.line with debit amount.
        with move_form.line_ids.new() as debit_line2:
            debit_line2.name = 'debit_line_2'
            debit_line2.account_id = self.account
            debit_line2.debit = 2000
            debit_line2.tax_ids.clear()
            debit_line2.tax_ids.add(self.percent_tax)

            self.assertTrue(debit_line2.recompute_tax_line)

        with move_form.line_ids.new() as credit_line2:
            credit_line2.name = 'credit_line_2'
            credit_line2.account_id = self.account
            credit_line2.credit = 2195

        move = move_form.save()

        self.assertRecordValues(move.line_ids, [
            {'name': 'credit_line_2',   'debit': 0.0,       'credit': 2195.0,   'tax_ids': [],                      'tax_line_id': False},
            {'name': 'debit_line_2',    'debit': 2000.0,    'credit': 0.0,      'tax_ids': [self.percent_tax.id],   'tax_line_id': False},
            {'name': 'credit_line_1',   'debit': 0.0,       'credit': 1105.0,   'tax_ids': [],                      'tax_line_id': False},
            {'name': 'tax_line',        'debit': 300.0,     'credit': 0.0,      'tax_ids': [],                      'tax_line_id': self.percent_tax.id},
            {'name': 'debit_line_1',    'debit': 1000.0,    'credit': 0.0,      'tax_ids': [self.percent_tax.id],   'tax_line_id': False},
        ])

    def test_onchange_taxes_4(self):
        '''
        Test an account.move.line is created automatically when adding a tax.
        This test uses the following scenario:
            - Create manually a debit line of 1000 having an included tax.
            - Assume a line containing the tax amount is created automatically.
            - Create manually a credit line to balance the two previous lines.
            - Save the move.

        included tax = 20%

        Name                   | Debit     | Credit    | Tax_ids       | Tax_line_id's name
        -----------------------|-----------|-----------|---------------|-------------------
        debit_line_1           | 1000      |           | tax           |
        included_tax_line      | 200       |           |               | included_tax_line
        credit_line_1          |           | 1200      |               |
        '''
        move_form = Form(self.env['account.move'], view='account.view_move_form')
        move_form.ref = 'azerty'
        move_form.journal_id = self.journal

        # Create a new account.move.line with debit amount.
        with move_form.line_ids.new() as debit_line:
            debit_line.name = 'debit_line_1'
            debit_line.account_id = self.account
            debit_line.debit = 1000
            debit_line.tax_ids.clear()
            debit_line.tax_ids.add(self.included_percent_tax)

            self.assertTrue(debit_line.recompute_tax_line)

        # Create a third account.move.line with credit amount.
        with move_form.line_ids.new() as credit_line:
            credit_line.name = 'credit_line_1'
            credit_line.account_id = self.account
            credit_line.credit = 1200

        move = move_form.save()

        self.assertRecordValues(move.line_ids, [
            {'name': 'credit_line_1',            'debit': 0.0,       'credit': 1200.0,   'tax_ids': [],                                  'tax_line_id': False},
            {'name': 'included_tax_line',        'debit': 200.0,     'credit': 0.0,      'tax_ids': [],                                  'tax_line_id': self.included_percent_tax.id},
            {'name': 'debit_line_1',             'debit': 1000.0,    'credit': 0.0,      'tax_ids': [self.included_percent_tax.id],      'tax_line_id': False},
        ])
