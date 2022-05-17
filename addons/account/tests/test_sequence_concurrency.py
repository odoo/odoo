import threading
import time

import psycopg2

import odoo
from odoo import SUPERUSER_ID, api, fields
from odoo.tests import Form, TransactionCase, tagged


@tagged("post_install", "-at_install", "test_move_sequence")
class TestSequenceConcurrency(TransactionCase):
    def setUp(self):
        super().setUp()
        self.product = self.env.ref("product.product_delivery_01")
        self.partner = self.env.ref("base.res_partner_12")
        self.date = fields.Date.to_date("1985-04-14")

    def _create_invoice_form(self, env, post=True):
        with Form(
            env["account.move"].with_context(default_move_type="out_invoice")
        ) as invoice_form:
            invoice_form.partner_id = self.partner
            invoice_form.invoice_date = self.date
            with invoice_form.invoice_line_ids.new() as line_form:
                line_form.product_id = self.product
                line_form.price_unit = 100.0
                line_form.tax_ids.clear()
            invoice = invoice_form.save()
        if post:
            invoice.action_post()
        return invoice

    def _create_payment_form(self, env):
        with Form(
            env["account.payment"].with_context(
                default_payment_type="inbound",
                default_partner_type="customer",
                default_move_journal_types=("bank", "cash"),
            )
        ) as payment_form:
            payment_form.partner_id = env.ref("base.res_partner_12")
            payment_form.amount = 100
            payment_form.date = self.date
            payment = payment_form.save()
        payment.action_post()
        return payment

    def _clean_moves(self, move_ids):
        """Delete moves created after finish unittest using
        self.addCleanup(self._clean_moves, self.env, (invoices | payments.mapped('move_id')).ids)"""
        with self.env.registry.cursor() as cr:
            env = api.Environment(cr, SUPERUSER_ID, {})
            moves = env["account.move"].browse(move_ids)
            moves.button_draft()
            moves.write({"posted_before": False})
            moves.unlink()
            env.cr.commit()

    def test_sequence_concurrency_payments(self):
        """Creating concurrent payments should not raises errors"""
        with self.env.registry.cursor() as cr0, self.env.registry.cursor() as cr1, self.env.registry.cursor() as cr2:
            env0 = api.Environment(cr0, SUPERUSER_ID, {})
            env1 = api.Environment(cr1, SUPERUSER_ID, {})
            env2 = api.Environment(cr2, SUPERUSER_ID, {})
            for cr in [cr0, cr1, cr2]:
                # Set 10s timeout in order to avoid waiting for release locks a long time
                cr.execute("SET LOCAL statement_timeout = '10s'")

            # Create "last move" to lock
            payment = self._create_payment_form(env0)
            self.addCleanup(self._clean_moves, payment.move_id.ids)
            env0.cr.commit()
            try:
                with env1.cr.savepoint(), env2.cr.savepoint():
                    self._create_payment_form(env1)
                    self._create_payment_form(env2)
            except (
                psycopg2.errors.QueryCanceled,
                psycopg2.errors.TransactionRollbackError,
            ) as e:
                self.assertFalse(
                    True,
                    "Should it raises error to user and rollback the whole transaction? %s"
                    % e,
                )

    def test_sequence_concurrency_draft_invoices(self):
        """Creating 2 DRAFT invoices not should raises errors"""
        with self.env.registry.cursor() as cr0, self.env.registry.cursor() as cr1, self.env.registry.cursor() as cr2:
            env0 = api.Environment(cr0, SUPERUSER_ID, {})
            env1 = api.Environment(cr1, SUPERUSER_ID, {})
            env2 = api.Environment(cr2, SUPERUSER_ID, {})
            for cr in [cr0, cr1, cr2]:
                # Set 10s timeout in order to avoid waiting for release locks a long time
                cr.execute("SET LOCAL statement_timeout = '10s'")

            # Create "last move" to lock
            invoice = self._create_invoice_form(env0)
            self.addCleanup(self._clean_moves, invoice.ids)
            env0.cr.commit()
            try:
                with env1.cr.savepoint(), env2.cr.savepoint():
                    invoice1 = self._create_invoice_form(env1, post=False)
                    self.assertEqual(invoice1.state, "draft")
                    invoice2 = self._create_invoice_form(env2, post=False)
                    self.assertEqual(invoice2.state, "draft")
            except (
                psycopg2.errors.QueryCanceled,
                psycopg2.errors.TransactionRollbackError,
            ) as e:
                self.assertFalse(
                    True,
                    "Should it raises error to user and rollback the whole transaction? %s"
                    % e,
                )

    def _create_invoice_payment(self, deadlock_timeout, payment_first=False):
        try:
            with odoo.api.Environment.manage():
                with self.env.registry.cursor() as cr:
                    # Avoid waiting for a long time and it needs to be less than deadlock
                    cr.execute(
                        "SET LOCAL statement_timeout = '%ss'", (deadlock_timeout + 10,)
                    )
                    env = api.Environment(cr, SUPERUSER_ID, {})
                    if payment_first:
                        self._create_payment_form(env)
                        self._create_invoice_form(env)
                    else:
                        self._create_invoice_form(env)
                        self._create_payment_form(env)
                    # sleep in order to avoid release the locks too faster
                    # It could be many methods called after creating these kind of records e.g. reconcile
                    time.sleep(deadlock_timeout + 12)
        except Exception as exc:
            self.last_thread_exc = exc
            raise exc

    def test_sequence_concurrency_pay2inv_inv2pay(self):
        """Creating concurrent payment then invoice and invoice then payment
        should not raises errors
        It raises deadlock sometimes"""
        with self.env.registry.cursor() as cr0:
            env0 = api.Environment(cr0, SUPERUSER_ID, {})

            # Create "last move" to lock
            invoice = self._create_invoice_form(env0)

            # Create "last move" to lock
            payment = self._create_payment_form(env0)
            self.addCleanup(self._clean_moves, (invoice | payment.move_id).ids)
            env0.cr.commit()
            env0.cr.execute(
                "SELECT setting FROM pg_settings WHERE name = 'deadlock_timeout'"
            )
            deadlock_timeout = int(env0.cr.fetchone()[0])  # ms
            # You could not have permission to set this parameter psycopg2.errors.InsufficientPrivilege
            self.assertTrue(
                deadlock_timeout,
                "You need to configure PG parameter deadlock_timeout='1s'",
            )
            deadlock_timeout = int(deadlock_timeout / 1000)  # s
            try:
                t_pay_inv = threading.Thread(
                    target=self._create_invoice_payment,
                    args=(deadlock_timeout, True),
                    name="Thread payment invoice",
                )
                t_inv_pay = threading.Thread(
                    target=self._create_invoice_payment,
                    args=(deadlock_timeout, False),
                    name="Thread invoice payment",
                )
                t_pay_inv.start()
                t_inv_pay.start()
                t_pay_inv.join(timeout=deadlock_timeout * 3)
                t_inv_pay.join(timeout=deadlock_timeout * 3)
                if self.last_thread_exc:
                    raise self.last_thread_exc
            except psycopg2.errors.DeadlockDetected as e:
                self.assertFalse(
                    True,
                    "Should it raises deadlock error to user and rollback the whole 2 transactions? %s"
                    % e,
                )
            except (
                psycopg2.errors.QueryCanceled,
                psycopg2.errors.TransactionRollbackError,
            ) as e:
                self.assertFalse(
                    True,
                    "Should it raises error to user and rollback the whole transaction? %s"
                    % e,
                )

    def test_sequence_concurrency_editing_last_invoice(self):
        """Edit last invoice and create a new invoice
        should not raises errors"""
        with self.env.registry.cursor() as cr0, self.env.registry.cursor() as cr1:
            env0 = api.Environment(cr0, SUPERUSER_ID, {})
            env1 = api.Environment(cr1, SUPERUSER_ID, {})
            for cr in [cr0, cr1]:
                # Set 10s timeout in order to avoid waiting for release locks a long time
                cr.execute("SET LOCAL statement_timeout = '10s'")

            # Create "last move" to lock
            invoice = self._create_invoice_form(env0)

            self.addCleanup(self._clean_moves, invoice.ids)
            env0.cr.commit()
            try:
                with env0.cr.savepoint(), env1.cr.savepoint():
                    # Edit something in "last move"
                    invoice.write({"ref": "Only changing ref"})
                    invoice.flush()
                    self._create_invoice_form(env1)
            except (
                psycopg2.errors.QueryCanceled,
                psycopg2.errors.TransactionRollbackError,
            ) as e:
                self.assertFalse(
                    True,
                    "Should it raises error to user and rollback the whole transaction? %s"
                    % e,
                )

    def test_sequence_concurrency_editing_last_payment(self):
        """Edit last payment and create a new payment
        should not raises errors"""
        with self.env.registry.cursor() as cr0, self.env.registry.cursor() as cr1:
            env0 = api.Environment(cr0, SUPERUSER_ID, {})
            env1 = api.Environment(cr1, SUPERUSER_ID, {})
            for cr in [cr0, cr1]:
                # Set 10s timeout in order to avoid waiting for release locks a long time
                cr.execute("SET LOCAL statement_timeout = '10s'")

            # Create "last move" to lock
            payment = self._create_payment_form(env0)

            self.addCleanup(self._clean_moves, payment.move_id.ids)
            env0.cr.commit()
            try:
                with env0.cr.savepoint(), env1.cr.savepoint():
                    # Edit something in "last move"
                    payment.write({"ref": "Only changing ref"})
                    payment.flush()
                    self._create_payment_form(env1)
            except (
                psycopg2.errors.QueryCanceled,
                psycopg2.errors.TransactionRollbackError,
            ) as e:
                self.assertFalse(
                    True,
                    "Should it raises error to user and rollback the whole transaction? %s"
                    % e,
                )

    def test_sequence_concurrency_reconciling_last_invoice(self):
        """Reconcile last invoice and create a new one
        should not raises errors"""
        with self.env.registry.cursor() as cr0, self.env.registry.cursor() as cr1:
            env0 = api.Environment(cr0, SUPERUSER_ID, {})
            env1 = api.Environment(cr1, SUPERUSER_ID, {})
            for cr in [cr0, cr1]:
                # Set 10s timeout in order to avoid waiting for release locks a long time
                cr.execute("SET LOCAL statement_timeout = '10s'")

            # Create "last move" to lock
            invoice = self._create_invoice_form(env0)
            payment = self._create_payment_form(env0)
            self.addCleanup(self._clean_moves, (invoice | payment.move_id).ids)
            env0.cr.commit()
            payment_line = payment.line_ids.filtered(
                lambda l: l.account_id.internal_type == "receivable"
            )
            invoice_line = invoice.line_ids.filtered(
                lambda l: l.account_id.internal_type == "receivable"
            )
            try:
                with env0.cr.savepoint(), env1.cr.savepoint():
                    # Reconciling "last move"
                    # reconcile a payment with many invoices spend a lot so it could lock records too many time
                    (payment_line | invoice_line).reconcile()
                    # Many pieces of code call flush directly
                    payment_line.flush()
                    self._create_invoice_form(env1)
            except (
                psycopg2.errors.QueryCanceled,
                psycopg2.errors.TransactionRollbackError,
            ) as e:
                self.assertFalse(
                    True,
                    "Should it raises error to user and rollback the whole transaction? %s"
                    % e,
                )

    def test_sequence_concurrency_reconciling_last_payment(self):
        """Reconcile last payment and create a new one
        should not raises errors"""
        with self.env.registry.cursor() as cr0, self.env.registry.cursor() as cr1:
            env0 = api.Environment(cr0, SUPERUSER_ID, {})
            env1 = api.Environment(cr1, SUPERUSER_ID, {})
            for cr in [cr0, cr1]:
                # Set 10s timeout in order to avoid waiting for release locks a long time
                cr.execute("SET LOCAL statement_timeout = '10s'")

            # Create "last move" to lock
            invoice = self._create_invoice_form(env0)
            payment = self._create_payment_form(env0)
            self.addCleanup(self._clean_moves, (invoice | payment.move_id).ids)
            env0.cr.commit()
            payment_line = payment.line_ids.filtered(
                lambda l: l.account_id.internal_type == "receivable"
            )
            invoice_line = invoice.line_ids.filtered(
                lambda l: l.account_id.internal_type == "receivable"
            )
            try:
                with env0.cr.savepoint(), env1.cr.savepoint():
                    # Reconciling "last move"
                    # reconcile a payment with many invoices spend a lot so it could lock records too many time
                    (payment_line | invoice_line).reconcile()
                    # Many pieces of code call flush directly
                    payment_line.flush()
                    self._create_payment_form(env1)
            except (
                psycopg2.errors.QueryCanceled,
                psycopg2.errors.TransactionRollbackError,
            ) as e:
                self.assertFalse(
                    True,
                    "Should it raises error to user and rollback the whole transaction? %s"
                    % e,
                )
