from contextlib import closing

from datetime import timedelta

from freezegun import freeze_time

from odoo import Command, fields
from odoo.addons.account.models.company import SOFT_LOCK_DATE_FIELDS
from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.exceptions import UserError
from odoo.tests import new_test_user, tagged


@tagged('post_install', '-at_install')
class TestAccountLockException(AccountTestInvoicingCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.fakenow = cls.env.cr.now()
        cls.startClassPatcher(freeze_time(cls.fakenow))

        cls.other_user = new_test_user(
            cls.env,
            name='Other User',
            login='other_user',
            password='password',
            email='other_user@example.com',
            group_ids=cls.get_default_groups().ids,
            company_id=cls.env.company.id,
        )

        cls.company_data_2 = cls.setup_other_company()

        cls.soft_lock_date_info = [
            ('fiscalyear_lock_date', 'out_invoice'),
            ('tax_lock_date', 'out_invoice'),
            ('sale_lock_date', 'out_invoice'),
            ('purchase_lock_date', 'in_invoice'),
        ]

    def test_user_exception_move_edit_multi_user(self):
        """
        Test that an exception for a specific user only works for that user.
        """
        for lock_date_field, move_type in self.soft_lock_date_info:
            with self.subTest(lock_date_field=lock_date_field, move_type=move_type), closing(self.cr.savepoint()):
                move = self.init_invoice(move_type, invoice_date='2016-01-01', post=True, amounts=[1000.0], taxes=self.tax_sale_a)

                # Lock the move
                self.company[lock_date_field] = fields.Date.to_date('2020-01-01')
                with self.assertRaises(UserError):
                    move.button_draft()

                # Add an exception to make the move editable (for the current user)
                self.env['account.lock_exception'].create({
                    'company_id': self.company.id,
                    'user_id': self.env.user.id,
                    lock_date_field: fields.Date.to_date('2010-01-01'),
                    'end_datetime': self.fakenow + timedelta(hours=24),
                    'reason': 'test_user_exception_move_edit_multi_user',
                })
                move.button_draft()
                move.action_post()

                # Check that the exception does not apply to other users
                with self.assertRaises(UserError):
                    move.with_user(self.other_user).button_draft()

    def test_global_exception_move_edit_multi_user(self):
        """
        Test that an exception without a specified user works for any user.
        """
        for lock_date_field, move_type in self.soft_lock_date_info:
            with self.subTest(lock_date_field=lock_date_field, move_type=move_type), closing(self.cr.savepoint()):
                move = self.init_invoice(move_type, invoice_date='2016-01-01', post=True, amounts=[1000.0], taxes=self.tax_sale_a)

                # Lock the move
                self.company[lock_date_field] = fields.Date.to_date('2020-01-01')
                with self.assertRaises(UserError):
                    move.button_draft()

                # Add a global exception to make the move editable for everyone
                self.env['account.lock_exception'].create({
                    'company_id': self.company.id,
                    'user_id': False,
                    lock_date_field: fields.Date.to_date('2010-01-01'),
                    'end_datetime': self.fakenow + timedelta(hours=24),
                    'reason': 'test_global_exception_move_edit_multi_user',
                })

                move.button_draft()
                move.action_post()

                move.with_user(self.other_user).button_draft()


    def test_user_exception_branch(self):
        """
        Test that the locking and exception mechanism works correctly in company hierarchies.
            * A lock in the branch does not lock the parent.
            * A lock in the parent also locks the branch.
            * An exception in the branch does not matter for the lock in the parent.
            * Let both parent and branch be locked.
              To make changes in the locked period in the brranch we need exceptions in both companies.
        """

        root_company = self.company_data['company']
        root_company.write({'child_ids': [Command.create({'name': 'branch'})]})
        self.cr.precommit.run()  # load the CoA
        branch = root_company.child_ids

        for lock_date_field, move_type in self.soft_lock_date_info:
            with self.subTest(lock_date_field=lock_date_field, move_type=move_type), closing(self.cr.savepoint()):
                # Create a move in the branch
                branch_move = self.init_invoice(
                    move_type, invoice_date='2016-01-01', post=True, amounts=[1000.0], taxes=self.tax_sale_a, company=branch,
                )

                # Create a move in the parent company
                root_move = self.init_invoice(
                    move_type, invoice_date='2016-01-01', post=True, amounts=[1000.0], taxes=self.tax_sale_a, company=root_company,
                )

                # Lock the branch
                branch[lock_date_field] = fields.Date.to_date('2020-01-01')

                # The branch_move is locked while the root_move is not
                with self.assertRaises(UserError):
                    branch_move.button_draft()
                root_move.button_draft()
                root_move.action_post()

                # Add an exception in the branch to make the branch_move editable (for the current user)
                self.env['account.lock_exception'].create({
                    'company_id': branch.id,
                    'user_id': self.env.user.id,
                    lock_date_field: fields.Date.to_date('2010-01-01'),
                    'end_datetime': self.fakenow + timedelta(hours=24),
                    'reason': 'test_user_exception_branch branch exception',
                })
                branch_move.button_draft()
                branch_move.action_post()

                # Lock the parent company
                root_company[lock_date_field] = fields.Date.to_date('2020-01-01')

                # Check that both moves are locked now (the branch exception alone is insufficient)
                for move in [branch_move, root_move]:
                    with self.assertRaises(UserError):
                        move.button_draft()

                # Add an exception in the parent company to make both moves editable (for the current user)
                self.env['account.lock_exception'].create({
                    'company_id': root_company.id,
                    'user_id': self.env.user.id,
                    lock_date_field: fields.Date.to_date('2010-01-01'),
                    'end_datetime': self.fakenow + timedelta(hours=24),
                    'reason': 'test_user_exception_branch root_company exception',
                })
                for move in [branch_move, root_move]:
                    move.button_draft()
                    move.action_post()


    def test_user_exception_wrong_company(self):
        """
        Test that an exception only works for the specified company.
        """
        for lock_date_field, move_type in self.soft_lock_date_info:
            with self.subTest(lock_date_field=lock_date_field, move_type=move_type), closing(self.cr.savepoint()):
                move = self.init_invoice(move_type, invoice_date='2016-01-01', post=True, amounts=[1000.0], taxes=self.tax_sale_a)
                # Lock the move
                self.company[lock_date_field] = fields.Date.to_date('2020-01-01')
                with self.assertRaises(UserError):
                    move.button_draft()

                # Add an exception for another company
                self.env['account.lock_exception'].create({
                    'company_id': self.company_data_2['company'].id,
                    'user_id': self.env.user.id,
                    lock_date_field: fields.Date.to_date('2010-01-01'),
                    'end_datetime': self.fakenow + timedelta(hours=24),
                    'reason': 'test_user_exception_move_edit_multi_user',
                })

                # Check that the exception is insufficient
                with self.assertRaises(UserError):
                    move.button_draft()


    def test_user_exception_insufficient(self):
        """
        Test that the exception only works if the specified lock date is actually before the accounting date.
        """
        for lock_date_field, move_type in self.soft_lock_date_info:
            with self.subTest(lock_date_field=lock_date_field, move_type=move_type), closing(self.cr.savepoint()):
                move = self.init_invoice(move_type, invoice_date='2016-01-01', post=True, amounts=[1000.0], taxes=self.tax_sale_a)

                # Lock the move
                self.company[lock_date_field] = fields.Date.to_date('2020-01-01')
                with self.assertRaises(UserError):
                    move.button_draft()

                # Add an exception before the lock date but not before the date of the test_invoice
                self.env['account.lock_exception'].create({
                    'company_id': self.company.id,
                    'user_id': self.env.user.id,
                    lock_date_field: fields.Date.to_date('2016-01-01'),
                    'end_datetime': self.fakenow + timedelta(hours=24),
                    'reason': 'test_user_exception_move_edit_multi_user',
                })

                # Check that the exception is insufficient
                with self.assertRaises(UserError):
                    move.button_draft()


    def test_expired_exception(self):
        """
        Test that the exception does not work if we are past the `end_datetime` of the exception.
        """
        for lock_date_field, move_type in self.soft_lock_date_info:
            with self.subTest(lock_date_field=lock_date_field, move_type=move_type), closing(self.cr.savepoint()):
                move = self.init_invoice(move_type, invoice_date='2016-01-01', post=True, amounts=[1000.0], taxes=self.tax_sale_a)

                # Lock the move
                self.company[lock_date_field] = fields.Date.to_date('2020-01-01')
                with self.assertRaises(UserError):
                    move.button_draft()

                # Add an expired exception
                self.env['account.lock_exception'].create({
                    'company_id': self.company.id,
                    'user_id': self.env.user.id,
                    lock_date_field: fields.Date.to_date('2010-01-01'),
                    'create_date': self.fakenow - timedelta(hours=24),
                    'end_datetime': self.fakenow - timedelta(seconds=1),
                    'reason': 'test_expired_exception',
                })
                with self.assertRaises(UserError):
                    move.button_draft()


    def test_revoked_exception(self):
        for lock_date_field, move_type in self.soft_lock_date_info:
            with self.subTest(lock_date_field=lock_date_field, move_type=move_type), closing(self.cr.savepoint()):
                move = self.init_invoice(move_type, invoice_date='2016-01-01', post=True, amounts=[1000.0], taxes=self.tax_sale_a)

                # Lock the move
                self.company[lock_date_field] = fields.Date.to_date('2020-01-01')
                with self.assertRaises(UserError):
                    move.button_draft()

                # Add an exception to make the move editable (for the current user)
                exception = self.env['account.lock_exception'].create({
                    'company_id': self.company.id,
                    'user_id': self.env.user.id,
                    lock_date_field: fields.Date.to_date('2010-01-01'),
                    'end_datetime': self.fakenow + timedelta(hours=24),
                    'reason': 'test_user_exception_move_edit_multi_user',
                })
                move.button_draft()
                move.action_post()

                exception.action_revoke()

                # Check that the exception does not work anymore
                with self.assertRaises(UserError):
                    move.button_draft()


    def test_user_exception_wrong_field(self):
        for lock_date_field, move_type, exception_lock_date_field in [
            ('fiscalyear_lock_date', 'out_invoice', 'tax_lock_date'),
            ('tax_lock_date', 'out_invoice', 'fiscalyear_lock_date'),
            ('sale_lock_date', 'out_invoice', 'purchase_lock_date'),
            ('purchase_lock_date', 'in_invoice', 'sale_lock_date'),
        ]:
            with self.subTest(lock_date_field=lock_date_field, move_type=move_type), closing(self.cr.savepoint()):
                move = self.init_invoice(move_type, invoice_date='2016-01-01', post=True, amounts=[1000.0], taxes=self.tax_sale_a)
                # Lock the move
                self.company[lock_date_field] = fields.Date.to_date('2020-01-01')
                with self.assertRaises(UserError):
                    move.button_draft()

                # Add an exception for a different lock date field
                self.env['account.lock_exception'].create({
                    'company_id': self.company_data_2['company'].id,
                    'user_id': self.env.user.id,
                    exception_lock_date_field: fields.Date.to_date('2010-01-01'),
                    'end_datetime': self.fakenow + timedelta(hours=24),
                    'reason': 'test_user_exception_wrong_field',
                })

                # Check that the exception is insufficient
                with self.assertRaises(UserError):
                    move.button_draft()


    def test_hard_lock_date(self):
        """
        Test that
          * exceptions (for other lock date fields) do not allow bypassing the hard lock date
          * the hard lock date cannot be decreased or removed
        """
        in_move = self.init_invoice('in_invoice', invoice_date='2016-01-01', post=True, amounts=[1000.0], taxes=self.tax_sale_a)
        out_move = self.init_invoice('out_invoice', invoice_date='2016-01-01', post=True, amounts=[1000.0], taxes=self.tax_sale_a)

        self.company.hard_lock_date = fields.Date.to_date('2020-01-01')

        # Check that we cannot remove the hard lock date.
        with self.assertRaises(UserError):
            self.company.hard_lock_date = False

        # Check that we cannot decrease the hard lock date.
        with self.assertRaises(UserError):
            self.company.hard_lock_date = fields.Date.to_date('2019-01-01')

        # Create exceptions for all lock date fields except the hard lock date
        self.env['account.lock_exception'].create([
            {
            'company_id': self.company_data_2['company'].id,
            'user_id': self.env.user.id,
            lock_date_field: fields.Date.to_date('2010-01-01'),
            'end_datetime': self.fakenow + timedelta(hours=24),
            'reason': f'test_hard_lock_ignores_exceptions {lock_date_field}',
            }
            for lock_date_field in SOFT_LOCK_DATE_FIELDS
        ])

        # Check that the exceptions are insufficient
        for move in [in_move, out_move]:
            with self.assertRaises(UserError):
                move.button_draft()

    def test_company_lock_date(self):
        """
        Test the `company_lock_date` field is set corretly on exception creation.
        Test the behavior when a company lock date is changed.
          * Every active exception gets revoked and recreated with the new company lock date
          * Non-active exceptions are not affected
        """
        self.env['account.lock_exception'].search([]).sudo().unlink()
        for lock_date_field, move_type in self.soft_lock_date_info:
            with self.subTest(lock_date_field=lock_date_field, move_type=move_type), closing(self.cr.savepoint()):
                self.company[lock_date_field] = fields.Date.to_date('2020-01-01')

                revoked_exception = self.env['account.lock_exception'].create({
                    'company_id': self.company.id,
                    'user_id': self.env.user.id,
                    lock_date_field: fields.Date.to_date('2010-01-01'),
                    'end_datetime': self.fakenow + timedelta(hours=24),
                    'reason': 'test_exception_recreated_on_lock_date_change revoked',
                })
                revoked_exception.action_revoke()
                active_exception = self.env['account.lock_exception'].create({
                    'company_id': self.company.id,
                    'user_id': self.env.user.id,
                    lock_date_field: fields.Date.to_date('2010-01-01'),
                    'end_datetime': self.fakenow + timedelta(hours=24),
                    'reason': 'test_exception_recreated_on_lock_date_change active',
                })

                # Check that the company lock date field was set correcyly on exception creation
                self.assertEqual(revoked_exception.company_lock_date, fields.Date.to_date('2020-01-01'))
                self.assertEqual(active_exception.company_lock_date, fields.Date.to_date('2020-01-01'))

                # The lock date change should trigger the "recreation" proces
                self.company[lock_date_field] = fields.Date.to_date('2021-01-01')

                self.assertEqual(revoked_exception.company_lock_date, fields.Date.to_date('2020-01-01'))

                self.assertEqual(active_exception.state, 'revoked')

                exceptions = self.env['account.lock_exception'].with_context(active_test=False).search([])
                self.assertEqual(len(exceptions), 3)
                new_exception = exceptions - revoked_exception - active_exception
                # Check that the new exception is a "recreation" of the `active_exception`
                self.assertRecordValues(new_exception, [{
                    'company_id': self.company.id,
                    'user_id': self.env.user.id,
                    lock_date_field: fields.Date.to_date('2010-01-01'),
                    'company_lock_date': fields.Date.to_date('2021-01-01'),
                    'end_datetime': self.env.cr.now() + timedelta(hours=24),
                    'reason': 'test_exception_recreated_on_lock_date_change active',
                }])


    def test_user_exception_remove_lock_date(self):
        """
        Test that an exception removing a lock date (instead of just decreasing it) works.
        """
        for lock_date_field, move_type in self.soft_lock_date_info:
            with self.subTest(lock_date_field=lock_date_field, move_type=move_type), closing(self.cr.savepoint()):
                move = self.init_invoice(move_type, invoice_date='2016-01-01', post=True, amounts=[1000.0], taxes=self.tax_sale_a)

                # Lock the move
                self.company[lock_date_field] = fields.Date.to_date('2020-01-01')
                with self.assertRaises(UserError):
                    move.button_draft()

                # Add an exception removing the lock date
                self.env['account.lock_exception'].create({
                    'company_id': self.company.id,
                    'user_id': self.env.user.id,
                    lock_date_field: False,
                    'end_datetime': self.fakenow + timedelta(hours=24),
                    'reason': 'test_user_exception_move_edit_multi_user',
                })
                move.button_draft()

