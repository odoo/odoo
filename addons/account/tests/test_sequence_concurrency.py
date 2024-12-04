# pylint: disable=bad-builtin,missing-return,print-used,redundant-unittest-assert
import logging
import threading
import time
import unittest

import psycopg2

import odoo
from odoo import SUPERUSER_ID, api, fields, release, tools
from odoo.tests import Form, TransactionCase, tagged

PG_CONCURRENCY_ERRORS = [
    psycopg2.errorcodes.LOCK_NOT_AVAILABLE,
    psycopg2.errorcodes.SERIALIZATION_FAILURE,
    psycopg2.errorcodes.DEADLOCK_DETECTED,
    psycopg2.errorcodes.QUERY_CANCELED,
    psycopg2.errorcodes.TRANSACTION_ROLLBACK,
]

_logger = logging.getLogger(__name__)


class ThreadRaiseJoin(threading.Thread):
    """Custom Thread Class to raise the exception to main thread in the join"""

    def run(self, *args, **kwargs):
        self.exc = None
        try:
            return super().run(*args, **kwargs)
        except BaseException as e:  # noqa: BLE001
            self.exc = e

    def join(self, *args, **kwargs):
        super().join(*args, **kwargs)
        # raise exception in the join
        # to raise it in the main thread
        if self.exc:
            raise self.exc


@tagged("post_install", "-at_install", "test_move_sequence")
class TestSequenceConcurrency(TransactionCase):
    def setUp(self):
        super().setUp()
        self.product = self.env.ref("product.product_delivery_01")
        self.partner = self.env.ref("base.res_partner_12")
        self.date = fields.Date.to_date("1985-04-14")

    def _create_invoice_form(self, env, post=True):
        if release.version == "13.0":
            # It is not compatible for v14.0
            # issue related with attachments
            ctx = {"default_type": "out_invoice"}
        else:
            ctx = {"default_move_type": "out_invoice"}
        with Form(env["account.move"].with_context(**ctx)) as invoice_form:
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
            if "payment_date" in payment_form._view["fields"]:
                # odoo v13.0
                payment_form.payment_date = self.date
            else:
                # odoo v14.0
                payment_form.date = self.date

            payment = payment_form.save()
        if hasattr(payment, "post"):
            # Odoo v13.0
            payment.post()
        else:
            # Odoo v14.0
            payment.action_post()
        return payment

    def _clean_moves(self, move_ids, payment=None):
        """Delete moves created after finish unittest using
        self.addCleanup(self._clean_moves, self.env, (invoices | payments.mapped('move_id')).ids)"""
        with self.env.registry.cursor() as cr:
            env = api.Environment(cr, SUPERUSER_ID, {})
            moves = env["account.move"].browse(move_ids)
            moves.button_draft()
            if "posted_before" in moves._fields:
                # v14.0
                moves.write({"posted_before": False})
            else:
                # v13.0
                moves = moves.with_context(force_delete=True)
            moves.with_context(force_delete=True).unlink()
            # TODO: Delete payment and journal for v13.0 and v14.0
            env.cr.commit()

    def _create_invoice_payment(self, deadlock_timeout, payment_first=False):
        registry = odoo.registry(self.env.cr.dbname)
        with registry.cursor() as cr, cr.savepoint():
            env = api.Environment(cr, SUPERUSER_ID, {})
            cr_pid = cr.connection.get_backend_pid()
            # Avoid waiting for a long time and it needs to be less than deadlock
            cr.execute("SET LOCAL statement_timeout = '%ss'", (deadlock_timeout + 10,))
            if payment_first:
                # TODO: Check why if remove logger or print the thread let it alive
                _logger.info("Creating payment cr %s", cr_pid)
                self._create_payment_form(env)
                _logger.info("Creating invoice cr %s", cr_pid)
                self._create_invoice_form(env)
            else:
                _logger.info("Creating invoice cr %s", cr_pid)
                self._create_invoice_form(env)
                _logger.info("Creating payment cr %s", cr_pid)
                self._create_payment_form(env)
            # sleep in order to avoid release the locks too faster
            # It could be many methods called after creating these kind of records e.g. reconcile
            _logger.info("Finishing waiting %s", (deadlock_timeout + 12))
            time.sleep(deadlock_timeout + 12)

    def test_sequence_concurrency_10_draft_invoices(self):
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
            except psycopg2.OperationalError as e:
                if e.pgcode in PG_CONCURRENCY_ERRORS:
                    self.assertFalse(
                        True,
                        "Should it raises error to user and rollback the whole transaction? %s" % e,
                    )
                else:
                    raise

    def test_sequence_concurrency_20_editing_last_invoice(self):
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
                    invoice.write({"write_uid": env0.uid})
                    # invoice.flush()
                    env0.flush_all()
                    self._create_invoice_form(env1)
            except psycopg2.OperationalError as e:
                if e.pgcode in PG_CONCURRENCY_ERRORS:
                    self.assertFalse(
                        True,
                        "Should it raises error to user and rollback the whole transaction? %s" % e,
                    )
                else:
                    raise

    def test_sequence_concurrency_30_editing_last_payment(self):
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
            if hasattr(payment, "move_line_ids"):
                # v13.0
                payment_move = payment.mapped("move_line_ids.move_id")
            else:
                # v14.0
                payment_move = payment.move_id
            self.addCleanup(self._clean_moves, payment_move.ids)
            env0.cr.commit()
            try:
                with env0.cr.savepoint(), env1.cr.savepoint():
                    # Edit something in "last move"
                    payment_move.write({"write_uid": env0.uid})
                    # payment_move.flush()
                    env0.flush_all()
                    self._create_payment_form(env1)
            except (
                psycopg2.errors.QueryCanceled,
                psycopg2.errors.TransactionRollbackError,
                psycopg2.errors.LockNotAvailable,
            ) as e:
                self.assertFalse(
                    True,
                    "Should it raises error to user and rollback the whole transaction? %s" % e,
                )

    def test_sequence_concurrency_40_reconciling_last_invoice(self):
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
            if hasattr(payment, "move_line_ids"):
                # v13.0
                payment_move = payment.mapped("move_line_ids.move_id")
            else:
                # v14.0
                payment_move = payment.move_id
            self.addCleanup(self._clean_moves, invoice.ids + payment_move.ids)
            env0.cr.commit()
            lines2reconcile = (
                (payment_move | invoice)
                .mapped("line_ids")
                .filtered(lambda l: "receivable" in l.account_id.account_type)
            )
            try:
                with env0.cr.savepoint(), env1.cr.savepoint():
                    # Reconciling "last move"
                    # reconcile a payment with many invoices spend a lot so it could lock records too many time
                    lines2reconcile.reconcile()
                    # Many pieces of code call flush directly
                    # lines2reconcile.flush()
                    env0.flush_all()
                    self._create_invoice_form(env1)
            except psycopg2.OperationalError as e:
                if e.pgcode in PG_CONCURRENCY_ERRORS:
                    self.assertFalse(
                        True,
                        "Should it raises error to user and rollback the whole transaction? %s" % e,
                    )
                else:
                    raise

    def test_sequence_concurrency_50_reconciling_last_payment(self):
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
            if hasattr(payment, "move_line_ids"):
                # v13.0
                payment_move = payment.mapped("move_line_ids.move_id")
            else:
                # v14.0
                payment_move = payment.move_id
            self.addCleanup(self._clean_moves, invoice.ids + payment_move.ids)
            env0.cr.commit()
            lines2reconcile = (
                (payment_move | invoice)
                .mapped("line_ids")
                .filtered(lambda l: "receivable" in l.account_id.account_type)
            )
            try:
                with env0.cr.savepoint(), env1.cr.savepoint():
                    # Reconciling "last move"
                    # reconcile a payment with many invoices spend a lot so it could lock records too many time
                    lines2reconcile.reconcile()
                    # Many pieces of code call flush directly
                    # lines2reconcile.flush()
                    env0.flush_all()
                    self._create_payment_form(env1)
            except psycopg2.OperationalError as e:
                if e.pgcode in PG_CONCURRENCY_ERRORS:
                    self.assertFalse(
                        True,
                        "Should it raises error to user and rollback the whole transaction? %s" % e,
                    )
                else:
                    raise

    @unittest.skipIf(
        release.version == "13.0",
        "v13.0 you can define standard sequence for payments and avoid raising error here",
    )
    # TODO: Change the payment sequence to standard and revert it with commit
    def test_sequence_concurrency_90_invoices(self):
        """Creating concurrent invoices should not raises errors"""
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
                    self._create_invoice_form(env1)
                    self._create_invoice_form(env2)
            except psycopg2.OperationalError as e:
                if e.pgcode in PG_CONCURRENCY_ERRORS:
                    self.assertFalse(
                        True,
                        "Should it raises error to user and rollback the whole transaction? %s" % e,
                    )
                else:
                    raise

    @unittest.skipIf(
        release.version == "13.0",
        "v13.0 you can define standard sequence for payments and avoid raising error here",
    )
    # TODO: Change the payment sequence to standard and revert it with commit
    def test_sequence_concurrency_90_payments(self):
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
            if hasattr(payment, "move_line_ids"):
                # v13.0
                payment_move_ids = payment.mapped("move_line_ids.move_id").ids
            else:
                # v14.0
                payment_move_ids = payment.move_id.ids
            self.addCleanup(self._clean_moves, payment_move_ids)
            env0.cr.commit()
            try:
                with env1.cr.savepoint(), env2.cr.savepoint():
                    self._create_payment_form(env1)
                    self._create_payment_form(env2)
            except psycopg2.OperationalError as e:
                if e.pgcode in PG_CONCURRENCY_ERRORS:
                    self.assertFalse(
                        True,
                        "Should it raises error to user and rollback the whole transaction? %s" % e,
                    )
                else:
                    raise

    @tools.mute_logger("odoo.sql_db")
    def test_sequence_concurrency_95_pay2inv_inv2pay(self):
        """Creating concurrent payment then invoice and invoice then payment
        should not raises errors
        It raises deadlock sometimes"""
        # TODO: Check why v13.0 locks the records even when the method finishes
        with self.env.registry.cursor() as cr0:
            env0 = api.Environment(cr0, SUPERUSER_ID, {})

            # Create "last move" to lock
            invoice = self._create_invoice_form(env0)

            # Create "last move" to lock
            payment = self._create_payment_form(env0)
            if hasattr(payment, "move_line_ids"):
                # v13.0
                payment_move_ids = payment.mapped("move_line_ids.move_id").ids
            else:
                # v14.0
                payment_move_ids = payment.move_id.ids
            self.addCleanup(self._clean_moves, invoice.ids + payment_move_ids)
            env0.cr.commit()
            env0.cr.execute("SELECT setting FROM pg_settings WHERE name = 'deadlock_timeout'")
            deadlock_timeout = int(env0.cr.fetchone()[0])  # ms
            # You could not have permission to set this parameter psycopg2.errors.InsufficientPrivilege
            self.assertTrue(
                deadlock_timeout,
                "You need to configure PG parameter deadlock_timeout='1s'",
            )
            deadlock_timeout = int(deadlock_timeout / 1000)  # s
            try:
                t_pay_inv = ThreadRaiseJoin(
                    target=self._create_invoice_payment,
                    args=(deadlock_timeout, True),
                    name="Thread payment invoice",
                )
                t_inv_pay = ThreadRaiseJoin(
                    target=self._create_invoice_payment,
                    args=(deadlock_timeout, False),
                    name="Thread invoice payment",
                )
                t_pay_inv.start()
                t_inv_pay.start()
                t_pay_inv.join(timeout=deadlock_timeout + 15)
                t_inv_pay.join(timeout=deadlock_timeout + 15)
            except psycopg2.OperationalError as e:
                if e.pgcode == psycopg2.errorcodes.DEADLOCK_DETECTED:
                    self.assertFalse(
                        True,
                        "Should it raises deadlock error to user and rollback the whole 2 transactions? %s" % e,
                    )
                elif e.pgcode in PG_CONCURRENCY_ERRORS:
                    # Even if you could define invoice number as standard instead of no-gap in v13.0
                    # Odoo people said that the whole world needs to deal with sequence standard
                    # for all kind of invoices (bills, customer invoices, refunds)
                    # So not raises errors if not deadlock here
                    pass
                    # self.assertFalse(
                    #     True,
                    #     "Should it raises error to user and rollback the whole transaction? %s"
                    #     % e,
                    # )
                else:
                    raise
