# -*- coding: utf-8 -*-
import re

from odoo import Command
from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.addons.mail.tests.common import MailCase
from odoo.tests import tagged
from odoo.exceptions import UserError, ValidationError


@tagged('post_install', '-at_install', 'mail_track')
class TestAccountTax(AccountTestInvoicingCommon, MailCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company_data_2 = cls.setup_other_company()

    @classmethod
    def default_env_context(cls):
        # OVERRIDE
        return {}

    def set_up_and_use_tax(self):

        self.env['account.move'].create({
            'move_type': 'out_invoice',
            'date': '2023-01-01',
            'invoice_line_ids': [
                Command.create({
                    'name': 'invoice_line',
                    'quantity': 1.0,
                    'price_unit': 100.0,
                    'tax_ids': [Command.set(self.company_data['default_tax_sale'].ids)],
                }),
            ],
        })

        # Create two lines after creating the move so that those lines are not used in the move
        self.company_data['default_tax_sale'].write({
            'invoice_repartition_line_ids': [
                Command.create({'repartition_type': 'tax', 'factor_percent': 0.0}),
            ],
            'refund_repartition_line_ids': [
                Command.create({'repartition_type': 'tax', 'factor_percent': 0.0}),
            ],
        })

        self.flush_tracking()
        self.assertTrue(self.company_data['default_tax_sale'].is_used)

    def flush_tracking(self):
        """ Force the creation of tracking values. """
        self.env.flush_all()
        self.cr.flush()

    def test_changing_tax_company(self):
        ''' Ensure you can't change the company of an account.tax if there are some journal entries '''

        # Avoid duplicate key value violates unique constraint "account_tax_name_company_uniq".
        self.company_data['default_tax_sale'].name = 'test_changing_account_company'

        self.env['account.move'].create({
            'move_type': 'out_invoice',
            'date': '2019-01-01',
            'invoice_line_ids': [
                (0, 0, {
                    'name': 'invoice_line',
                    'quantity': 1.0,
                    'price_unit': 100.0,
                    'tax_ids': [(6, 0, self.company_data['default_tax_sale'].ids)],
                }),
            ],
        })

        with self.assertRaises(UserError):
            self.company_data['default_tax_sale'].company_id = self.company_data_2['company']

    def test_logging_of_tax_update_when_tax_is_used(self):
        """ Modifications of a used tax should be logged. """
        self.set_up_and_use_tax()
        self.flush_tracking()

        old_amount = self.company_data['default_tax_sale'].amount
        old_name = self.company_data['default_tax_sale'].name

        with self.mock_mail_gateway(), self.mock_mail_app():
            self.company_data['default_tax_sale'].write({
                'name': self.company_data['default_tax_sale'].name + ' MODIFIED',
                'amount': 21,
                'amount_type': 'fixed',
                'type_tax_use': 'purchase',
                'price_include_override': 'tax_included',
                'include_base_amount': True,
                'is_base_affected': False,
            })
            self.flush_tracking()
        track_msg = self._new_msgs
        self.assertEqual(len(track_msg), 1,
                         "Only 1 message should have been created when updating all the values.")
        # There are 7 tracked values in account.tax and we update each of them, each on should be included in the message
        self.assertMessageFields(
            track_msg, {
                'tracking_values': [
                    ('amount', 'float', old_amount, 21.0),
                    ('amount_type', 'selection', 'Percentage', 'Fixed'),
                    ('include_base_amount', 'boolean', False, True),
                    ('is_base_affected', 'boolean', True, False),
                    ('name', 'char', old_name, old_name + ' MODIFIED'),
                    ('price_include_override', 'selection', '', 'Tax Included'),
                    ('type_tax_use', 'selection', 'Sales', 'Purchases'),
                ],
            }
        )

    def test_logging_of_repartition_lines_addition_when_tax_is_used(self):
        """ Adding repartition lines in a used tax should be logged. """
        self.set_up_and_use_tax()
        self.flush_tracking()

        with self.mock_mail_gateway(), self.mock_mail_app():
            self.company_data['default_tax_sale'].write({
                'invoice_repartition_line_ids': [
                    Command.create({'repartition_type': 'tax', 'factor_percent': -100.0}),
                ],
                'refund_repartition_line_ids': [
                    Command.create({'repartition_type': 'tax', 'factor_percent': -100.0}),
                ],
            })
            self.flush_tracking()

        # tracking done using _track_add
        self.assertEqual(len(self._new_msgs), 2)
        for msg, exp_values in zip(self._new_msgs.sorted(lambda m: m.body), [
            {
                'body_content': '<b>New Invoice</b> repartition line 4',
                'tracking_values': [
                    (False, 'char', False, 'None', {'field_info': {'name': 'Account', 'desc': 'Account', 'type': 'char'}}),
                    (False, 'char', False, '-100.0', {'field_info': {'name': 'Factor Percent', 'desc': 'Factor Percent', 'type': 'char'}}),
                    (False, 'char', False, 'None', {'field_info': {'name': 'Tax Grids', 'desc': 'Tax Grids', 'type': 'char'}}),
                    (False, 'char', False, 'False', {'field_info': {'name': 'Use in tax closing', 'desc': 'Use in tax closing', 'type': 'char'}}),
                ],
            }, {
                'body_content': '<b>New Refund</b> repartition line 4',
                'tracking_values': [
                    (False, 'char', False, 'None', {'field_info': {'name': 'Account', 'desc': 'Account', 'type': 'char'}}),
                    (False, 'char', False, '-100.0', {'field_info': {'name': 'Factor Percent', 'desc': 'Factor Percent', 'type': 'char'}}),
                    (False, 'char', False, 'None', {'field_info': {'name': 'Tax Grids', 'desc': 'Tax Grids', 'type': 'char'}}),
                    (False, 'char', False, 'False', {'field_info': {'name': 'Use in tax closing', 'desc': 'Use in tax closing', 'type': 'char'}}),
                ],
            },
        ], strict=True):
            self.assertMessageFields(msg, {
                'body_content': '',
                'model': 'account.tax',
                'res_id': self.company_data['default_tax_sale'].id,
                'tracking_values': [],
                **exp_values,
            })

    def test_logging_of_repartition_lines_update_when_tax_is_used(self):
        """ Updating repartition lines in a used tax should be logged. """
        self.set_up_and_use_tax()
        self.flush_tracking()

        last_invoice_rep_line = self.company_data['default_tax_sale'].invoice_repartition_line_ids\
            .filtered(lambda tax_rep: not tax_rep.factor_percent)
        last_refund_rep_line = self.company_data['default_tax_sale'].refund_repartition_line_ids\
            .filtered(lambda tax_rep: not tax_rep.factor_percent)

        with self.mock_mail_gateway(), self.mock_mail_app():
            self.company_data['default_tax_sale'].write({
                "invoice_repartition_line_ids": [
                    Command.update(last_invoice_rep_line.id, {
                        'factor_percent': -100,
                        'tag_ids': [Command.create({'name': 'TaxTag12345'})]
                    }),
                ],
                "refund_repartition_line_ids": [
                    Command.update(last_refund_rep_line.id, {
                        'factor_percent': -100,
                        'account_id': self.company_data['default_account_tax_purchase'].id,
                    }),
                ],
            })
            self.flush_tracking()

        # tracking done using _track_add
        self.assertEqual(len(self._new_msgs), 2)
        for msg, exp_values in zip(self._new_msgs.sorted(lambda m: m.body, reverse=True), [
            {
                'body_content': '<b>Invoice</b> repartition line 3',
                'tracking_values': [
                    (False, 'char', '0.0', '-100.0', {'field_info': {'name': 'Factor Percent', 'desc': 'Factor Percent', 'type': 'char'}}),
                    (False, 'char', 'None', "['TaxTag12345']", {'field_info': {'name': 'Tax Grids', 'desc': 'Tax Grids', 'type': 'char'}}),
                ],
            }, {
                'body_content': '<b>Refund</b> repartition line 3',
                'tracking_values': [
                    (False, 'char', 'None', '131000 Tax Paid', {'field_info': {'name': 'Account', 'desc': 'Account', 'type': 'char'}}),
                    (False, 'char', '0.0', '-100.0', {'field_info': {'name': 'Factor Percent', 'desc': 'Factor Percent', 'type': 'char'}}),
                    (False, 'char', 'False', 'True', {'field_info': {'name': 'Use in tax closing', 'desc': 'Use in tax closing', 'type': 'char'}}),
                ],
            },
        ], strict=True):
            self.assertMessageFields(msg, {
                'body_content': '',
                'model': 'account.tax',
                'res_id': self.company_data['default_tax_sale'].id,
                'tracking_values': [],
                **exp_values,
            })

    def test_logging_of_repartition_lines_reordering_when_tax_is_used(self):
        """ Reordering repartition lines in a used tax should be logged. """
        self.set_up_and_use_tax()
        self.flush_tracking()

        last_invoice_rep_line = self.company_data['default_tax_sale'].invoice_repartition_line_ids\
            .filtered(lambda tax_rep: not tax_rep.factor_percent)
        last_refund_rep_line = self.company_data['default_tax_sale'].refund_repartition_line_ids\
            .filtered(lambda tax_rep: not tax_rep.factor_percent)

        with self.mock_mail_gateway(), self.mock_mail_app():
            self.company_data['default_tax_sale'].write({
                "invoice_repartition_line_ids": [
                    Command.update(last_invoice_rep_line.id, {'sequence': 0}),
                ],
                "refund_repartition_line_ids": [
                    Command.update(last_refund_rep_line.id, {'sequence': 0}),
                ],
            })
            self.flush_tracking()

        # tracking done using _track_add
        self.assertEqual(len(self._new_msgs), 6)
        messages = self._new_msgs.sorted(
            key=lambda m: (
                '<b>Invoice</b>' not in (m.body or ''),
                int(re.search(r'line (\d+)', m.body or '').group(1)) if re.search(r'line (\d+)', m.body or '') else 0
            )
        )

        for msg, exp_values in zip(messages, [
            {
                'body_content': '<b>Invoice</b> repartition line 1',
                'tracking_values': [
                    (False, 'char', '100.0', '0.0', {'field_info': {'name': 'Factor Percent', 'desc': 'Factor Percent', 'type': 'char'}}),
                ],
            }, {
                'body_content': '<b>Invoice</b> repartition line 2',
                'tracking_values': [
                    (False, 'char', '251000 Tax Received', 'None', {'field_info': {'name': 'Account', 'desc': 'Account', 'type': 'char'}}),
                    (False, 'char', 'True', 'False', {'field_info': {'name': 'Use in tax closing', 'desc': 'Use in tax closing', 'type': 'char'}}),
                ],
            }, {
                'body_content': '<b>Invoice</b> repartition line 3',
                'tracking_values': [
                    (False, 'char', 'None', '251000 Tax Received', {'field_info': {'name': 'Account', 'desc': 'Account', 'type': 'char'}}),
                    (False, 'char', '0.0', '100.0', {'field_info': {'name': 'Factor Percent', 'desc': 'Factor Percent', 'type': 'char'}}),
                    (False, 'char', 'False', 'True', {'field_info': {'name': 'Use in tax closing', 'desc': 'Use in tax closing', 'type': 'char'}}),
                ],
            }, {
                'body_content': '<b>Refund</b> repartition line 1',
                'tracking_values': [
                    (False, 'char', '100.0', '0.0', {'field_info': {'name': 'Factor Percent', 'desc': 'Factor Percent', 'type': 'char'}}),
                ],
            }, {
                'body_content': '<b>Refund</b> repartition line 2',
                'tracking_values': [
                    (False, 'char', '251000 Tax Received', 'None', {'field_info': {'name': 'Account', 'desc': 'Account', 'type': 'char'}}),
                    (False, 'char', 'True', 'False', {'field_info': {'name': 'Use in tax closing', 'desc': 'Use in tax closing', 'type': 'char'}}),
                ],
            }, {
                'body_content': '<b>Refund</b> repartition line 3',
                'tracking_values': [
                    (False, 'char', 'None', '251000 Tax Received', {'field_info': {'name': 'Account', 'desc': 'Account', 'type': 'char'}}),
                    (False, 'char', '0.0', '100.0', {'field_info': {'name': 'Factor Percent', 'desc': 'Factor Percent', 'type': 'char'}}),
                    (False, 'char', 'False', 'True', {'field_info': {'name': 'Use in tax closing', 'desc': 'Use in tax closing', 'type': 'char'}}),
                ],
            },
        ], strict=True):
            self.assertMessageFields(msg, {
                'body_content': '',
                'model': 'account.tax',
                'res_id': self.company_data['default_tax_sale'].id,
                'tracking_values': [],
                **exp_values,
            })

    def test_logging_of_repartition_lines_removal_when_tax_is_used(self):
        """ Deleting repartition lines in a used tax should be logged. """
        self.set_up_and_use_tax()
        self.flush_tracking()

        last_invoice_rep_line = self.company_data['default_tax_sale'].invoice_repartition_line_ids.sorted(key=lambda r: r.sequence)[-1]
        last_refund_rep_line = self.company_data['default_tax_sale'].refund_repartition_line_ids.sorted(key=lambda r: r.sequence)[-1]

        with self.mock_mail_gateway(), self.mock_mail_app():
            self.company_data['default_tax_sale'].write({
                "invoice_repartition_line_ids": [
                    Command.delete(last_invoice_rep_line.id),
                ],
                "refund_repartition_line_ids": [
                    Command.delete(last_refund_rep_line.id),
                ],
            })
            self.flush_tracking()

        # manual log, no tracking
        self.assertEqual(len(self._new_msgs), 2)
        for msg, exp_values in zip(self._new_msgs.sorted(lambda m: m.body), [
            {
                'body_content': '<b>Removed Invoice</b> repartition line 3',
                'tracking_values': [
                    (False, 'char', False, 'None', {'field_info': {'name': 'Account', 'desc': 'Account', 'type': 'char'}}),
                    (False, 'char', False, 'None', {'field_info': {'name': 'Tax Grids', 'desc': 'Tax Grids', 'type': 'char'}}),
                    (False, 'char', False, 'False', {'field_info': {'name': 'Use in tax closing', 'desc': 'Use in tax closing', 'type': 'char'}}),
                ],
            }, {
                'body_content': '<b>Removed Refund</b> repartition line 3',
                'tracking_values': [
                    (False, 'char', False, 'None', {'field_info': {'name': 'Account', 'desc': 'Account', 'type': 'char'}}),
                    (False, 'char', False, 'None', {'field_info': {'name': 'Tax Grids', 'desc': 'Tax Grids', 'type': 'char'}}),
                    (False, 'char', False, 'False', {'field_info': {'name': 'Use in tax closing', 'desc': 'Use in tax closing', 'type': 'char'}}),
                ],
            },
        ], strict=True):
            self.assertMessageFields(msg, {
                'body_content': '',
                'model': 'account.tax',
                'res_id': self.company_data['default_tax_sale'].id,
                'tracking_values': [],
                **exp_values,
            })

    def test_message_log(self):
        """ Somehow assert people did not break primitives of mail.thread """
        new_tax = self.env['account.tax'].create({
            'name': 'default_tax',
            'amount_type': 'fixed',
            'amount': 10.0,
        })
        self.flush_tracking()
        self.assertFalse(new_tax.is_used)
        message = new_tax._message_log(body='A note for future usage')
        self.assertMessageFields(message, {'body': '<p>A note for future usage</p>'})

        with self.mock_mail_gateway(), self.mock_mail_app():
            new_tax.write({'name': 'New name, do not track'})
            self.flush_tracking()
        self.assertEqual(len(self._new_msgs), 1)
        self.assertMessageFields(self._new_msgs, {'body': '', 'tracking_values': [('name', 'char', 'default_tax', 'New name, do not track')]})

    def test_tax_is_used_when_in_transactions(self):
        ''' Ensures that a tax is set to used when it is part of some transactions '''

        # Account.move is one type of transaction
        tax_invoice = self.env['account.tax'].create({
            'name': 'test_is_used_invoice',
            'amount': '100',
        })

        self.env['account.move'].create({
            'move_type': 'out_invoice',
            'date': '2023-01-01',
            'invoice_line_ids': [
                Command.create({
                    'name': 'invoice_line',
                    'quantity': 1.0,
                    'price_unit': 100.0,
                    'tax_ids': [Command.set(tax_invoice.ids)],
                }),
            ],
        })
        tax_invoice.invalidate_model(fnames=['is_used'])
        self.assertTrue(tax_invoice.is_used)

        # Account.reconcile is another of transaction
        tax_reconciliation = self.env['account.tax'].create({
            'name': 'test_is_used_reconcilition',
            'amount': '100',
        })
        self.env['account.reconcile.model'].create({
            'name': "test_tax_is_used",
            'line_ids': [Command.create({
                'account_id': self.company_data['default_account_revenue'].id,
                'tax_ids': [Command.set(tax_reconciliation.ids)],
            })],
        })
        tax_reconciliation.invalidate_model(fnames=['is_used'])
        self.assertTrue(tax_reconciliation.is_used)

    def test_tax_no_duplicate_in_repartition_line(self):
        """ Test that whenever a tax generate a second tax line
            the same tax is not applied to the tax line.
        """

        account_1 = self.company_data['default_account_tax_sale'].copy()
        account_2 = self.company_data['default_account_tax_sale'].copy()
        tax = self.env['account.tax'].create({
            'name': "tax",
            'amount': 15.0,
            'include_base_amount': True,
            'invoice_repartition_line_ids': [
                Command.create({
                    'repartition_type': 'base',
                }),
                Command.create({
                    'factor_percent': 100,
                    'repartition_type': 'tax',
                    'account_id': account_1.id,
                }),
                Command.create({
                    'factor_percent': -100,
                    'repartition_type': 'tax',
                    'account_id': account_2.id,
                }),
            ],
            'refund_repartition_line_ids': [
                Command.create({
                    'repartition_type': 'base',
                }),
                Command.create({
                    'factor_percent': 100,
                    'repartition_type': 'tax',
                    'account_id': account_1.id,
                }),
                Command.create({
                    'factor_percent': -100,
                    'repartition_type': 'tax',
                    'account_id': account_2.id,
                }),
            ],
        })

        invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'date': '2019-01-01',
            'invoice_line_ids': [
                Command.create({
                    'name': 'invoice_line',
                    'quantity': 1.0,
                    'price_unit': 100.0,
                    'tax_ids': [Command.set(tax.ids)],
                }),
            ],
        })

        self.assertRecordValues(invoice, [{
            'amount_untaxed': 100.0,
            'amount_tax': 0.0,
            'amount_total': 100.0,
        }])
        self.assertRecordValues(invoice.line_ids, [
            {'display_type': 'product',         'tax_ids': tax.ids,     'balance': -100.0,  'account_id': self.company_data['default_account_revenue'].id},
            {'display_type': 'tax',             'tax_ids': [],          'balance': -15.0,   'account_id': account_1.id},
            {'display_type': 'tax',             'tax_ids': [],          'balance': 15.0,    'account_id': account_2.id},
            {'display_type': 'payment_term',    'tax_ids': [],          'balance': 100.0,   'account_id': self.company_data['default_account_receivable'].id},
        ])

    def test_cannot_delete_group_tax_in_use(self):
        """ Test that a group of taxes (parent tax) cannot be deleted when it's used. """

        sales_10_perc = self.env['account.tax'].create({
            'name': '10% Sales tax',
            'amount': 10.0,
            'amount_type': 'percent',
            'type_tax_use': 'sale',
        })
        sales_5_perc = self.env['account.tax'].create({
            'name': '5% Sales tax',
            'amount': 5.0,
            'amount_type': 'percent',
            'type_tax_use': 'sale',
        })
        # Group of taxes
        sales_15_perc = self.env['account.tax'].create({
            'name': '15% Sales tax',
            'amount': 15.0,
            'amount_type': 'group',
            'type_tax_use': 'sale',
            'children_tax_ids': [Command.set([sales_10_perc.id, sales_5_perc.id])],
        })
        self.env['account.move'].create({
            'move_type': 'out_invoice',
            'date': '2025-01-01',
            'invoice_line_ids': [
                Command.create({
                    'name': 'invoice_line',
                    'quantity': 1.0,
                    'price_unit': 100.0,
                    'tax_ids': [Command.set(sales_15_perc.ids)],
                }),
            ],
        })
        self.assertTrue(sales_15_perc.is_used)
        with self.assertRaisesRegex(ValidationError, "delete taxes that are currently in use"):
            sales_15_perc.unlink()

    def test_negative_factor_percent(self):
        account_1 = self.company_data['default_account_tax_sale'].copy()
        with self.assertRaisesRegex(ValidationError, r"Invoice and credit note distribution should have a total factor \(\+\) equals to 100\."):
            self.env['account.tax'].create({
                'name': "tax",
                'amount': 15.0,
                'include_base_amount': True,
                'invoice_repartition_line_ids': [
                    Command.create({
                        'repartition_type': 'base',
                    }),
                    Command.create({
                        'factor_percent': -100,
                        'repartition_type': 'tax',
                        'account_id': account_1.id,
                    }),
                ],
                'refund_repartition_line_ids': [
                    Command.create({
                        'repartition_type': 'base',
                    }),
                    Command.create({
                        'factor_percent': -100,
                        'repartition_type': 'tax',
                        'account_id': account_1.id,
                    }),
                ],
            })
