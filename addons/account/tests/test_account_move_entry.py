# -*- coding: utf-8 -*-
from odoo.addons.account.tests.invoice_test_common import InvoiceTestCommon
from odoo.tests import tagged
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
        with self.assertRaises((ValidationError, UserError)):
            self.test_move.company_id.fiscalyear_lock_date = fields.Date.from_string('2017-01-01')

        self.cr.execute('''UPDATE res_company SET fiscalyear_lock_date = '2017-01-01' WHERE id = %s''', self.test_move.company_id.ids)

        with self.assertRaises((ValidationError, UserError)):
            self.test_move.post()

        with self.assertRaises(UserError):
            self.env['account.move'].create(self.test_move.copy_data())

    def test_misc_tax_lock_date_1(self):
        # Set the tax lock date after the journal entry date.
        self.test_move.company_id.tax_lock_date = fields.Date.from_string('2017-01-01')

        # lines[0] = 'counterpart line'
        # lines[1] = 'tax line'
        # lines[2] = 'revenue line 1'
        # lines[3] = 'revenue line 2'
        lines = self.test_move.line_ids.sorted('debit')

        # Writing not affecting a tax is allowed.
        self.test_move.write({
            'line_ids': [
                (1, lines[0].id, {'credit': 1750.0}),   # counterpart line
                (1, lines[2].id, {'debit': 600.0}),     # revenue line 1
            ],
        })

        self.cr.execute('SAVEPOINT test_misc_tax_lock_date_1')

        # Writing something affecting a tax is not allowed.
        with self.assertRaises(ValidationError):
            self.test_move.write({
                'line_ids': [
                    (1, lines[0].id, {'credit': 2750.0}),
                    (1, lines[3].id, {'debit': 2000.0}),
                ],
            })

        with self.assertRaises(ValidationError):
            self.test_move.write({
                'line_ids': [
                    (1, lines[3].id, {'tax_ids': [(6, 0, self.company_data['default_tax_purchase'].ids)]}),
                ],
            })

        with self.assertRaises(ValidationError):
            self.test_move.write({
                'line_ids': [
                    (1, lines[0].id, {'credit': 1900.0}),
                    (1, lines[1].id, {'debit': 300.0}),
                ],
            })

        with self.assertRaises(ValidationError):
            self.test_move.unlink()

        self.cr.execute('ROLLBACK TO SAVEPOINT test_misc_tax_lock_date_1')

        with self.assertRaises(UserError):
            self.test_move.post()
