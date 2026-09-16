import json
import logging
import os
import socket
import threading
import time
import traceback
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import datetime, timedelta
from enum import StrEnum
from functools import partial
from typing import Any

import psycopg.errors

from odoo import api, db, fields, models
from odoo.db.errors import PG_RETRY_EXCEPTIONS
from odoo.exceptions import (
    ConcurrencyError,
    MissingError,
    RetryableJobError,
    TerminalJobError,
    UserError,
    ValidationError,
)
from odoo.libs import backoff
from odoo.libs.debug_log import DebugLog
from odoo.libs.worker_thread import working_on_database
from odoo.models import GC_UNLINK_LIMIT
from odoo.modules.registry import Registry
from odoo.service import get_job_real_time_budget
from odoo.tools import SQL
from odoo.tools.constants import JOB_QUEUE_CHANNEL

from .ir_cron import (
    PG_CONCURRENCY_ERRORS,
    BadModuleStateError,
    BadVersionError,
    IrCron,
    is_user_archived,
    notify_channel,
    schedule_notify_after_commit,
)

_logger = logging.getLogger(__name__)
_debug = DebugLog(__name__)

NOTIFY_PENDING_KEY = "ir.job.notify"

ALLOWED_CONTEXT_KEYS = ("lang", "tz", "allowed_company_ids")

DEAD_JOB_GRACE_S = 60

RETRY_BACKOFF_BASE_S = 10
RETRY_BACKOFF_MAX_S = 3600

CLAIM_MAX_ATTEMPTS = 10
CLAIM_BACKOFF_BASE_S = 0.05
CLAIM_BACKOFF_MAX_S = 1.0

CONCURRENCY_MAX_ATTEMPTS = 5
CONCURRENCY_BACKOFF_BASE_S = 0.2
CONCURRENCY_BACKOFF_MAX_S = 2.0
JOB_CONCURRENCY_EXCEPTIONS = (*PG_CONCURRENCY_ERRORS, ConcurrencyError)

DRAIN_BUDGET_RATIO = 0.4

MAINTENANCE_INTERVAL_S = 30
REAP_BATCH_SIZE = 1000

DONE_RETENTION = timedelta(days=7)
FAILED_RETENTION = timedelta(days=30)

_last_maintenance: dict[str, float] = {}


class JobState(StrEnum):
    WAIT_DEPS = "wait_deps"
    SCHEDULED = "scheduled"
    PENDING = "pending"
    STARTED = "started"
    DONE = "done"
    FAILED = "failed"
    CANCELLED = "cancelled"


STATES = [
    (JobState.WAIT_DEPS, "Waiting Dependencies"),
    (JobState.SCHEDULED, "Scheduled"),
    (JobState.PENDING, "Pending"),
    (JobState.STARTED, "Started"),
    (JobState.DONE, "Done"),
    (JobState.FAILED, "Failed"),
    (JobState.CANCELLED, "Cancelled"),
]

QUEUED_STATES = (
    JobState.WAIT_DEPS,
    JobState.SCHEDULED,
    JobState.PENDING,
    JobState.STARTED,
)

CANCELLABLE_STATES = (JobState.WAIT_DEPS, JobState.SCHEDULED, JobState.PENDING)

RUNNABLE_STATES = (JobState.SCHEDULED, JobState.PENDING)

REQUEUABLE_STATES = (JobState.FAILED, JobState.CANCELLED)

_DUE_STATE_SQL = SQL(
    "CASE WHEN eta IS NULL OR eta <= (now() AT TIME ZONE 'UTC')"
    " THEN 'pending' ELSE 'scheduled' END"
)

DEAD_DEPENDENCY_STATES = (JobState.FAILED, JobState.CANCELLED)

CLAIMED_COLUMNS = SQL(
    "id, uuid, channel, priority, model_name, method_name, record_ids, args,"
    " kwargs, user_id, company_id, context, retry, max_retries, defer_count,"
    " max_defers"
)


class ClaimContended(Exception):
    pass


def _states_sql(states: tuple[JobState, ...]) -> str:
    return "(" + ", ".join(f"'{state.value}'" for state in states) + ")"


QUEUED_STATES_SQL = _states_sql(QUEUED_STATES)


def _format_exception(exc: BaseException) -> str:
    return "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))


def _current_job() -> dict | None:
    return getattr(threading.current_thread(), "ir_job", None)


@contextmanager
def _running_job(job: dict[str, Any]) -> Iterator[None]:
    thread = threading.current_thread()
    previous = getattr(thread, "ir_job", None)
    thread.ir_job = job
    try:
        yield
    finally:
        thread.ir_job = previous


def _get_job_config(model_cls: type, method_name: str) -> dict | None:
    for klass in model_cls.__mro__:
        func = klass.__dict__.get(method_name)
        if func is not None and (job_config := getattr(func, "_job_config", None)):
            return job_config
    return None


def _advisory_key_sql(job_id: int | SQL) -> SQL:
    return SQL("hashtextextended('ir_job:' || %s::text, 0)", job_id)


@contextmanager
def _job_session_lock(cr, job_id: int, *, blocking: bool = True) -> Iterator[bool]:
    if blocking:
        cr.execute(SQL("SELECT pg_advisory_lock(%s)", _advisory_key_sql(job_id)))
        acquired = True
    else:
        cr.execute(SQL("SELECT pg_try_advisory_lock(%s)", _advisory_key_sql(job_id)))
        acquired = cr.fetchone()[0]
        _debug.logic("session_lock.tried", job=job_id, acquired=acquired)
    try:
        yield acquired
    finally:
        if acquired:
            _release_job_session_lock(cr, job_id)


def _release_job_session_lock(cr, job_id: int) -> None:
    unlock = SQL("SELECT pg_advisory_unlock(%s)", _advisory_key_sql(job_id))
    try:
        cr.execute(unlock)
    except psycopg.errors.InFailedSqlTransaction:
        _logger.info(
            "Job %s: its transaction is aborted, releasing the liveness lock "
            "after the rollback",
            job_id,
        )
        _debug.logic("session_lock.release_deferred", job=job_id, reason="aborted")
        cr.postrollback.add(partial(cr.execute, unlock))
    except psycopg.Error:
        _logger.warning(
            "Job %s: could not release its liveness lock, "
            "leaving it to the connection pool",
            job_id,
        )
        _debug.logic("session_lock.release_failed", job=job_id, reason="pg_error")


class DelayedProxy:
    __slots__ = ("_props", "_records")

    def __init__(self, records: models.BaseModel, props: dict[str, Any]) -> None:
        self._records = records
        self._props = props

    def __getattr__(self, name: str):
        if name.startswith("__") and name.endswith("__"):
            raise AttributeError(name)
        records, props = self._records, self._props

        def enqueue(*args: Any, **kwargs: Any) -> models.BaseModel:
            return records.env["ir.job"]._enqueue(
                records, name, args=args, kwargs=kwargs, **props
            )

        return enqueue


class Base(models.AbstractModel):
    _inherit = "base"

    @api.private
    def delayed(
        self,
        *,
        priority: int | None = None,
        eta: Any = None,
        channel: str | None = None,
        max_retries: int | None = None,
        identity_key: str | None = None,
        after: models.BaseModel | None = None,
        name: str | None = None,
    ) -> DelayedProxy:
        return DelayedProxy(
            self,
            {
                "priority": priority,
                "eta": eta,
                "channel": channel,
                "max_retries": max_retries,
                "identity_key": identity_key,
                "after": after,
                "name": name,
            },
        )


class IrJobChannel(models.Model):
    _name = "ir.job.channel"
    _description = "Background Job Channel"
    _order = "name"
    _allow_sudo_commands = False

    name = fields.Char(required=True)
    capacity = fields.Integer(
        default=1,
        required=True,
        help="Maximum number of jobs of this channel running concurrently, "
        "across all job workers. A channel with no record of its own is not "
        "capped here at all: its concurrency is whatever the worker fleet "
        "provides. Create a record to restrict a channel below that.",
    )
    active = fields.Boolean(
        default=True,
        help="Archived channels are paused: none of their jobs is claimed "
        "until the channel is restored.",
    )
    running_count = fields.Integer(
        string="Running",
        compute="_compute_job_counts",
        help="Jobs of this channel currently executing, across all workers.",
    )
    pending_count = fields.Integer(
        string="Pending",
        compute="_compute_job_counts",
        help="Jobs of this channel waiting to be claimed.",
    )

    _name_uniq = models.UniqueIndex("(name)", "Channel names must be unique.")
    _check_capacity = models.Constraint(
        "CHECK(capacity > 0)",
        "The channel capacity must be strictly positive.",
    )

    @api.depends("name")
    def _compute_job_counts(self) -> None:
        counts = {
            (channel, state): count
            for channel, state, count in self.env["ir.job"]
            .sudo()
            ._read_group(
                [
                    ("channel", "in", self.mapped("name")),
                    ("state", "in", (JobState.STARTED, JobState.PENDING)),
                ],
                ["channel", "state"],
                ["__count"],
            )
        }
        _debug.perf.count("channel.counts_read", channels=len(self), rows=len(counts))
        for record in self:
            record.running_count = counts.get((record.name, JobState.STARTED), 0)
            record.pending_count = counts.get((record.name, JobState.PENDING), 0)


class IrJob(models.Model):
    _name = "ir.job"
    _description = "Background Job"
    _order = "priority, create_date, id"
    _allow_sudo_commands = False

    name = fields.Char(
        readonly=True,
        help="Optional human-readable label shown instead of "
        "the technical model.method display name.",
    )
    uuid = fields.Char(
        index=True,
        readonly=True,
    )
    channel = fields.Char(
        default="root",
        readonly=True,
        required=True,
    )
    state = fields.Selection(
        selection=STATES,
        default=JobState.PENDING,
        index=True,
        required=True,
    )
    priority = fields.Integer(
        default=10,
        readonly=True,
    )
    eta = fields.Datetime(
        string="Execute After",
        help="Earliest execution time (empty: ASAP).",
    )
    identity_key = fields.Char(readonly=True)

    model_name = fields.Char(
        readonly=True,
        required=True,
    )
    method_name = fields.Char(
        readonly=True,
        required=True,
    )
    record_ids = fields.Json(readonly=True)
    args = fields.Json(readonly=True)
    kwargs = fields.Json(readonly=True)
    user_id = fields.Many2one(
        comodel_name="res.users",
        readonly=True,
        required=True,
    )
    company_id = fields.Many2one(
        comodel_name="res.company",
        readonly=True,
    )
    context = fields.Json(readonly=True)

    retry = fields.Integer(
        default=0,
        readonly=True,
    )
    max_retries = fields.Integer(
        default=5,
        readonly=True,
    )
    defer_count = fields.Integer(
        default=0,
        readonly=True,
        help="Times the job asked to be run again later. A deferral is not a "
        "failure, so it has its own budget and does not consume a retry.",
    )
    max_defers = fields.Integer(
        default=100,
        readonly=True,
    )
    defer_reason = fields.Char(
        readonly=True,
        help="Why the job last asked to be run again later.",
    )
    exc_name = fields.Char(readonly=True)
    exc_message = fields.Char(readonly=True)
    exc_info = fields.Text(readonly=True)

    started_at = fields.Datetime(readonly=True)
    done_at = fields.Datetime(readonly=True)
    worker_ident = fields.Char(readonly=True)

    depends_on_ids = fields.Many2many(
        comodel_name="ir.job",
        relation="ir_job_dependency",
        column1="job_id",
        column2="depends_on_id",
        readonly=True,
        help="This job stays in 'Waiting Dependencies' until every listed "
        "job is done; it is cancelled if any of them fails.",
    )
    dependent_ids = fields.Many2many(
        comodel_name="ir.job",
        relation="ir_job_dependency",
        column1="depends_on_id",
        column2="job_id",
        string="Dependents",
        readonly=True,
    )

    _claim_idx = models.Index(
        "(channel, priority, create_date, id) WHERE state = 'pending'"
    )
    _due_idx = models.Index("(eta) WHERE state = 'scheduled'")
    _capacity_idx = models.Index("(channel) WHERE state = 'started'")
    _retention_idx = models.Index(
        "(done_at) WHERE state IN ('done', 'failed', 'cancelled')"
    )
    _identity_uniq = models.UniqueIndex(
        f"(identity_key) WHERE state IN {QUEUED_STATES_SQL}"
        " AND identity_key IS NOT NULL",
        "A job with the same identity key is already queued.",
    )

    @api.constrains("depends_on_ids", "dependent_ids")
    def _check_dependency_cycle(self) -> None:
        if self._has_cycle("depends_on_ids"):
            raise ValidationError(self.env._("Job dependencies cannot form a cycle."))

    @api.job(max_retries=0)
    def _job_ping(self, message: str = "") -> None:
        _logger.info("ir.job ping: %s", message or "pong")

    @api.model
    def _enqueue(
        self,
        records: models.BaseModel,
        method_name: str,
        *,
        args: tuple = (),
        kwargs: dict | None = None,
        priority: int | None = None,
        eta: Any = None,
        channel: str | None = None,
        max_retries: int | None = None,
        identity_key: str | None = None,
        after: models.BaseModel | None = None,
        name: str | None = None,
    ) -> models.BaseModel:
        job_config = self._check_job_method(records, method_name)
        args_json, kwargs_json = self._dump_job_arguments(
            records, method_name, args, kwargs
        )

        env = self.env
        now = env.cr.now().replace(microsecond=0)
        state, eta, dep_ids = self._get_enqueue_state(eta, after)

        context = {
            key: env.context[key] for key in ALLOWED_CONTEXT_KEYS if key in env.context
        }
        row = self._insert_job_row(
            [
                name,
                channel or job_config["channel"],
                state,
                priority if priority is not None else job_config["priority"],
                eta or None,
                identity_key,
                records._name,
                method_name,
                json.dumps(records.ids),
                args_json,
                kwargs_json,
                env.uid,
                env.company.id,
                json.dumps(context),
                max_retries if max_retries is not None else job_config["max_retries"],
                job_config["max_defers"],
                env.uid,
                now,
                env.uid,
                now,
            ]
        )
        _debug.lifecycle(
            "enqueue",
            job=row[0] if row else None,
            model=records._name,
            method=method_name,
            records=len(records),
            state=str(state),
            channel=channel or job_config["channel"],
            deduplicated=row is None,
            depends_on=dep_ids,
        )
        if row is None:
            row = self._reuse_deduplicated_job(
                records, method_name, identity_key, dep_ids
            )
        elif dep_ids:
            _debug.pipeline(
                "enqueue.dependencies_linked", job=row[0], count=len(dep_ids)
            )
            env.cr.execute(
                SQL(
                    "INSERT INTO ir_job_dependency (job_id, depends_on_id)"
                    " SELECT %s, dep FROM unnest(%s::int[]) AS dep",
                    row[0],
                    dep_ids,
                )
            )
        if state == JobState.PENDING:
            _debug.pipeline("enqueue.notify_scheduled", job=row[0] if row else None)
            self._notify_after_commit(env.cr)
        return self.browse(row[0])

    def _check_job_method(
        self, records: models.BaseModel, method_name: str
    ) -> dict[str, Any]:
        job_config = _get_job_config(type(records), method_name)
        if job_config is None:
            _debug.logic(
                "enqueue.refused",
                reason="not_job_method",
                model=records._name,
                method=method_name,
            )
            raise UserError(
                self.env._(
                    "Method %(model)s.%(method)s cannot be enqueued: it is not "
                    "declared with @api.job.",
                    model=records._name,
                    method=method_name,
                )
            )
        if len(records) != len(records.ids):
            _debug.logic(
                "enqueue.refused",
                reason="unsaved_records",
                model=records._name,
                method=method_name,
            )
            raise UserError(
                self.env._(
                    "Cannot enqueue %(model)s.%(method)s on unsaved records: "
                    "the job would run against no record at all.",
                    model=records._name,
                    method=method_name,
                )
            )
        return job_config

    def _dump_job_arguments(
        self,
        records: models.BaseModel,
        method_name: str,
        args: tuple,
        kwargs: dict | None,
    ) -> tuple[str, str]:
        try:
            return json.dumps(list(args)), json.dumps(dict(kwargs or {}))
        except (TypeError, ValueError) as exc:
            _debug.logic(
                "enqueue.refused",
                reason="args_not_json",
                model=records._name,
                method=method_name,
                error=type(exc).__name__,
            )
            raise UserError(
                self.env._(
                    "Job arguments for %(model)s.%(method)s must be "
                    "JSON-serializable: %(error)s",
                    model=records._name,
                    method=method_name,
                    error=exc,
                )
            ) from exc

    def _get_enqueue_state(
        self, eta: Any, after: models.BaseModel | None
    ) -> tuple[str, Any, list[int]]:
        state = JobState.PENDING
        if eta is not None:
            clock_now = self._get_clock_timestamp()
            if isinstance(eta, (int, float)):
                eta = clock_now.replace(microsecond=0) + timedelta(seconds=eta)
            if eta and eta > clock_now:
                state = JobState.SCHEDULED
                _debug.logic("enqueue.scheduled", eta=eta)

        dep_ids: list[int] = []
        if not after:
            return state, eta, dep_ids

        if after._name != self._name:
            _debug.logic(
                "enqueue.refused", reason="dependency_model", model=after._name
            )
            raise UserError(self.env._("Job dependencies must be ir.job records."))
        self.env.cr.execute(
            SQL(
                "SELECT id, state FROM ir_job WHERE id IN %s",
                tuple(after.ids),
            )
        )
        dep_rows = self.env.cr.fetchall()
        dep_ids = [row[0] for row in dep_rows]
        dep_states = {row[1] for row in dep_rows}
        if dep_states & set(DEAD_DEPENDENCY_STATES):
            _debug.logic(
                "enqueue.refused", reason="dead_dependency", dependencies=len(dep_ids)
            )
            raise UserError(
                self.env._(
                    "Cannot enqueue after a failed or cancelled job; "
                    "requeue the dependency first."
                )
            )
        if dep_states - {JobState.DONE}:
            state = JobState.WAIT_DEPS
        _debug.logic(
            "enqueue.dependencies",
            count=len(dep_ids),
            waiting=state == JobState.WAIT_DEPS,
        )
        return state, eta, dep_ids

    def _insert_job_row(self, values: list) -> tuple | None:
        self.env.cr.execute(
            SQL(
                f"""
                INSERT INTO ir_job (
                    name, uuid, channel, state, priority, eta, identity_key,
                    model_name, method_name, record_ids, args, kwargs,
                    user_id, company_id, context, retry, max_retries,
                    defer_count, max_defers,
                    create_uid, create_date, write_uid, write_date
                ) VALUES (
                    %s, gen_random_uuid()::varchar, %s, %s, %s, %s, %s,
                    %s, %s, %s::jsonb, %s::jsonb, %s::jsonb,
                    %s, %s, %s::jsonb, 0, %s,
                    0, %s,
                    %s, %s, %s, %s
                )
                ON CONFLICT (identity_key)
                    WHERE state IN {QUEUED_STATES_SQL}
                    AND identity_key IS NOT NULL
                    DO NOTHING
                RETURNING id
                """,
                *values,
            )
        )
        return self.env.cr.fetchone()

    def _reuse_deduplicated_job(
        self,
        records: models.BaseModel,
        method_name: str,
        identity_key: str | None,
        dep_ids: list[int],
    ) -> tuple | None:
        self.env.cr.execute(
            SQL(
                "SELECT id FROM ir_job WHERE identity_key = %s"
                f" AND state IN {QUEUED_STATES_SQL}"
                " ORDER BY id DESC LIMIT 1",
                identity_key,
            )
        )
        row = self.env.cr.fetchone()
        _debug.logic(
            "enqueue.deduplicated",
            existing=row[0] if row else None,
            chained_lost=bool(dep_ids),
        )
        if dep_ids:
            _logger.warning(
                "ir.job %s.%s deduplicated on identity key %r: the job it "
                "was chained after (%s) is NOT a dependency of the "
                "existing job %s, which may therefore run first",
                records._name,
                method_name,
                identity_key,
                dep_ids,
                row[0] if row else None,
            )
        return row

    @api.model
    def _defer(self, seconds: int, reason: str = "") -> None:
        job = _current_job()
        if job is None:
            _debug.logic("defer.refused", reason="not_in_job")
            raise UserError(
                self.env._("_defer() can only be called from inside a running job.")
            )
        if job["defer_count"] >= job["max_defers"]:
            _debug.logic(
                "defer.refused",
                reason="budget_exhausted",
                job=job["id"],
                count=job["defer_count"],
            )
            raise TerminalJobError(
                self.env._(
                    "Job %(id)s asked to be deferred %(count)s times, its "
                    "whole budget, and is still not finished.",
                    id=job["id"],
                    count=job["defer_count"],
                )
            )
        job["defer"] = {"seconds": max(int(seconds), 0), "reason": reason or ""}
        _debug.logic("defer_requested", job=job["id"], seconds=seconds, reason=reason)

    @api.model
    def _get_clock_timestamp(self) -> datetime:
        self.env.cr.execute("SELECT (clock_timestamp() AT TIME ZONE 'UTC')")
        return self.env.cr.fetchone()[0]

    @staticmethod
    def _notify_after_commit(cr) -> None:
        def notify(db_name: str) -> None:
            IrJob._notify_workers(db_name)

        schedule_notify_after_commit(cr, NOTIFY_PENDING_KEY, notify)

    @staticmethod
    def _notify_workers(db_name: str) -> None:
        notify_channel(JOB_QUEUE_CHANNEL, db_name)

    @staticmethod
    def _process_jobs(db_name: str) -> None:
        with working_on_database(db_name):
            try:
                db_conn = db.db_connect(db_name)
                with db_conn.cursor() as pre_cr:
                    IrCron._check_version(pre_cr)
                    if IrCron._is_any_module_changing(pre_cr):
                        raise BadModuleStateError
                IrJob._run_maintenance(db_conn)
                IrJob._run_promotion(db_conn)
                with db_conn.cursor() as pre_cr:
                    pre_cr.execute(
                        "SELECT EXISTS (SELECT 1 FROM ir_job WHERE state = 'pending')"
                    )
                    if not pre_cr.fetchone()[0]:
                        _debug.logic("process.idle", db=db_name)
                        return
                _debug.pipeline("process.drain", db=db_name)
                IrJob._claim_and_run_loop(db_name, deadline=IrJob._drain_deadline())
            except BadVersionError:
                _logger.warning(
                    "Skipping database %s as its base version is not current.", db_name
                )
                _debug.logic("process.skipped", db=db_name, reason="bad_version")
            except BadModuleStateError:
                _logger.warning(
                    "Skipping database %s because of modules to install/upgrade/remove.",
                    db_name,
                )
                _debug.logic("process.skipped", db=db_name, reason="modules_changing")
            except psycopg.errors.UndefinedTable:
                _logger.debug("No ir_job table on database %s.", db_name)
                _debug.logic("process.skipped", db=db_name, reason="no_table")
            except db.PoolError:
                _logger.info("Skipping database %s: could not connect.", db_name)
                _debug.logic("process.skipped", db=db_name, reason="pool_error")
            except Exception:
                _logger.exception("Unexpected exception in job queue for %s:", db_name)

    @staticmethod
    def _drain_deadline() -> float | None:
        budget = get_job_real_time_budget()
        _debug.logic("drain.budget", seconds=budget, ratio=DRAIN_BUDGET_RATIO)
        return time.monotonic() + budget * DRAIN_BUDGET_RATIO if budget else None

    @staticmethod
    def _promote_due_jobs(cr) -> int:
        cr.execute(
            "UPDATE ir_job SET state = 'pending',"
            " write_date = (now() AT TIME ZONE 'UTC')"
            " WHERE state = 'scheduled'"
            " AND (eta IS NULL OR eta <= (now() AT TIME ZONE 'UTC'))"
        )
        if cr.rowcount:
            _logger.debug("Promoted %s scheduled job(s) now due", cr.rowcount)
            _debug.pipeline("promoted", count=cr.rowcount)
        return cr.rowcount

    @staticmethod
    def _run_promotion(db_conn) -> int:
        with db_conn.cursor() as cr:
            cr.execute(
                "SELECT pg_try_advisory_xact_lock("
                "hashtextextended('ir_job_promote', 0))"
            )
            if not cr.fetchone()[0]:
                _debug.logic("promotion.skipped", db=db_conn.dbname, reason="lock_held")
                return 0
            promoted = IrJob._promote_due_jobs(cr)
            cr.commit()
        return promoted

    @staticmethod
    def _run_maintenance(db_conn) -> None:
        now = time.monotonic()
        if (
            now - _last_maintenance.get(db_conn.dbname, float("-inf"))
            < MAINTENANCE_INTERVAL_S
        ):
            _debug.logic("maintenance.skipped", db=db_conn.dbname, reason="interval")
            return
        _last_maintenance[db_conn.dbname] = now
        with db_conn.cursor() as cr:
            cr.execute(
                "SELECT pg_try_advisory_xact_lock(hashtextextended('ir_job_gc', 0))"
            )
            if not cr.fetchone()[0]:
                _debug.logic(
                    "maintenance.skipped", db=db_conn.dbname, reason="lock_held"
                )
                return
            try:
                with _debug.perf("maintenance", cr=cr, db=db_conn.dbname):
                    IrJob._reap_dead_jobs(cr)
                    IrJob._release_ready_dependents(cr)
                cr.commit()
            except PG_RETRY_EXCEPTIONS as exc:
                cr.rollback()
                _logger.info(
                    "Job maintenance sweep of %s lost a race with a worker (%s);"
                    " the next sweep repeats it",
                    db_conn.dbname,
                    type(exc).__name__,
                )
                _debug.logic(
                    "maintenance.lost_race",
                    db=db_conn.dbname,
                    error=type(exc).__name__,
                )

    @staticmethod
    def _claim_and_run_loop(
        db_name: str,
        *,
        channels: list[str] | None = None,
        deadline: float | None = None,
    ) -> bool:
        registry = Registry(db_name).check_signaling()
        worker_ident = f"{socket.gethostname()}:{os.getpid()}"
        with registry.cursor() as cr:
            serialise = IrJob._has_job_channel(cr)
            cr.rollback()
            _debug.pipeline(
                "drain.begin",
                db=db_name,
                worker=worker_ident,
                serialise=serialise,
                channels=len(channels) if channels else 0,
            )
            while True:
                if deadline is not None and time.monotonic() >= deadline:
                    _logger.info(
                        "Job drain of %s yielded on its time budget; notifying",
                        db_name,
                    )
                    _debug.logic("drain.yielded", db=db_name, reason="deadline")
                    IrJob._notify_workers(db_name)
                    return True
                try:
                    job = IrJob._claim_next(
                        cr, worker_ident, channels, serialise=serialise
                    )
                except ClaimContended as exc:
                    cr.rollback()
                    _logger.warning(
                        "Job drain of %s: %s; notifying so the backlog is retried",
                        db_name,
                        exc,
                    )
                    _debug.logic("drain.yielded", db=db_name, reason="contended")
                    IrJob._notify_workers(db_name)
                    return True
                if job is None:
                    _debug.pipeline("drain.done", db=db_name)
                    cr.rollback()
                    return False
                _debug.lifecycle(
                    "job_claimed",
                    job=job["id"],
                    channel=job["channel"],
                    model=job["model_name"],
                    method=job["method_name"],
                    retry=job["retry"],
                )
                if (reloaded := registry.check_signaling()) is not registry:
                    _debug.lifecycle("drain.registry_reloaded", db=db_name)
                    registry = reloaded
                    cr.transaction.reset()
                cr.commit()
                with _job_session_lock(cr, job["id"]):
                    with _debug.perf("job_run", cr=cr, job=job["id"]) as span:
                        exc = IrJob._run_with_concurrency_replay(registry, cr, job)
                        span.set(failed=exc is not None)
                    if exc is None:
                        registry.signal_changes()
                        continue
                    IrJob._log_job_failure(job, exc)
                    registry[IrJob._name]._record_failure(cr, job, exc)
                    cr.commit()

    @staticmethod
    def _run_with_concurrency_replay(
        registry, cr, job: dict[str, Any]
    ) -> BaseException | None:
        for attempt in range(1, CONCURRENCY_MAX_ATTEMPTS + 1):
            try:
                registry[IrJob._name]._run_claimed(cr, job)
                cr.commit()
                return None
            except Exception as exc:
                registry.reset_changes()
                cr.rollback()
                if not isinstance(exc, JOB_CONCURRENCY_EXCEPTIONS):
                    _debug.logic(
                        "job.raised",
                        job=job["id"],
                        attempt=attempt,
                        error=type(exc).__name__,
                    )
                    return exc
                _debug.logic(
                    "job_concurrency_replay",
                    job=job["id"],
                    attempt=attempt,
                    error=type(exc).__name__,
                )
                if attempt == CONCURRENCY_MAX_ATTEMPTS:
                    _logger.info(
                        "Job %s: %s on every one of %s attempts, recording it",
                        job["id"],
                        type(exc).__name__,
                        CONCURRENCY_MAX_ATTEMPTS,
                    )
                    return exc
                wait = backoff.get_delay(
                    attempt,
                    base=CONCURRENCY_BACKOFF_BASE_S,
                    cap=CONCURRENCY_BACKOFF_MAX_S,
                )
                _logger.info(
                    "Job %s: %s, replaying in %.2fs (attempt %s/%s)",
                    job["id"],
                    type(exc).__name__,
                    wait,
                    attempt,
                    CONCURRENCY_MAX_ATTEMPTS,
                )
                time.sleep(wait)
        raise AssertionError("the replay loop always returns")

    @staticmethod
    def _log_job_failure(job: dict[str, Any], exc: BaseException) -> None:
        if isinstance(exc, RetryableJobError):
            return
        target = f"{job['model_name']}.{job['method_name']}"
        if isinstance(exc, UserError):
            _logger.warning("Job %s (%s) refused: %s", job["id"], target, exc)
        else:
            _logger.error("Job %s (%s) failed", job["id"], target, exc_info=exc)

    @staticmethod
    def _get_runnable_channels(cr, channels: list[str] | None = None) -> list[str]:
        cr.execute(
            SQL(
                """
                WITH RECURSIVE pending_channel AS (
                    (SELECT channel FROM ir_job
                      WHERE state = 'pending' ORDER BY channel LIMIT 1)
                    UNION ALL
                    SELECT (SELECT j.channel FROM ir_job j
                             WHERE j.state = 'pending' AND j.channel > p.channel
                             ORDER BY j.channel LIMIT 1)
                      FROM pending_channel p WHERE p.channel IS NOT NULL
                )
                SELECT p.channel
                FROM pending_channel p
                LEFT JOIN ir_job_channel c ON c.name = p.channel
                WHERE p.channel IS NOT NULL
                  %s
                  AND COALESCE(c.active, TRUE)
                  AND (c.capacity IS NULL
                       OR (SELECT count(*) FROM ir_job b
                            WHERE b.state = 'started' AND b.channel = p.channel)
                           < c.capacity)
                """,
                (
                    SQL("AND p.channel = ANY(%s)", list(channels))
                    if channels is not None
                    else SQL()
                ),
            )
        )
        runnable = [row[0] for row in cr.fetchall()]
        _debug.perf.count(
            "claim.runnable_channels",
            count=len(runnable),
            filtered=channels is not None,
        )
        return runnable

    @staticmethod
    def _has_job_channel(cr) -> bool:
        cr.execute("SELECT EXISTS (SELECT 1 FROM ir_job_channel)")
        return cr.fetchone()[0]

    @staticmethod
    def _claim_next(
        cr,
        worker_ident: str,
        channels: list[str] | None = None,
        serialise: bool = True,
    ) -> dict[str, Any] | None:
        for attempt in range(1, CLAIM_MAX_ATTEMPTS + 1):
            try:
                if serialise:
                    cr.execute(
                        "SELECT pg_advisory_xact_lock("
                        "hashtextextended('ir_job_claim', 0))"
                    )
                runnable = IrJob._get_runnable_channels(cr, channels)
                if not runnable:
                    _debug.logic("claim.none", reason="no_runnable_channel")
                    return None
                cr.execute(
                    SQL(
                        """
                        SELECT best.id
                        FROM unnest(%s::varchar[]) AS runnable(channel)
                        CROSS JOIN LATERAL (
                            SELECT j.id, j.priority, j.create_date
                            FROM ir_job j
                            WHERE j.state = 'pending'
                              AND j.channel = runnable.channel
                              AND (j.eta IS NULL
                                   OR j.eta <= (now() AT TIME ZONE 'UTC'))
                            ORDER BY j.priority, j.create_date, j.id
                            LIMIT 1
                        ) best
                        ORDER BY best.priority, best.create_date, best.id
                        LIMIT 1
                        """,
                        runnable,
                    )
                )
                picked = cr.fetchone()
                if picked is None:
                    _debug.logic(
                        "claim.none", reason="nothing_due", channels=len(runnable)
                    )
                    return None
                cr.execute(
                    SQL(
                        """
                        UPDATE ir_job
                        SET state = 'started',
                            started_at = (now() AT TIME ZONE 'UTC'),
                            worker_ident = %s,
                            write_date = (now() AT TIME ZONE 'UTC')
                        WHERE id = %s AND state = 'pending'
                        RETURNING %s
                        """,
                        worker_ident,
                        picked[0],
                        CLAIMED_COLUMNS,
                    )
                )
            except PG_RETRY_EXCEPTIONS:
                cr.rollback()
                _debug.logic("claim_retry", attempt=attempt, reason="serialization")
                if attempt < CLAIM_MAX_ATTEMPTS:
                    time.sleep(
                        backoff.get_delay(
                            attempt,
                            base=CLAIM_BACKOFF_BASE_S,
                            cap=CLAIM_BACKOFF_MAX_S,
                        )
                    )
                continue
            row = cr.fetchone()
            if row is not None:
                _debug.perf.count("claim.won", attempt=attempt, serialise=serialise)
                return dict(zip([d.name for d in cr.description], row, strict=True))
            _debug.logic("claim_retry", attempt=attempt, reason="lost_race")
            if attempt < CLAIM_MAX_ATTEMPTS:
                continue
        _debug.logic("claim.contended", attempts=CLAIM_MAX_ATTEMPTS)
        raise ClaimContended(
            f"job claim lost {CLAIM_MAX_ATTEMPTS} serialization races in a row"
        )

    @staticmethod
    def _get_claimed_target(
        cr, job: dict[str, Any]
    ) -> tuple[api.Environment, models.BaseModel]:
        env = api.Environment(cr, job["user_id"], dict(job["context"] or {}))
        env.transaction.default_env = env
        if is_user_archived(env):
            _debug.logic("job.terminal", job=job["id"], reason="user_archived")
            raise TerminalJobError(
                env._(
                    "Job %(id)s runs as %(login)s, whose account has been "
                    "archived since the job was enqueued.",
                    id=job["id"],
                    login=env.user.login,
                )
            )
        env = IrJob._narrow_company_scope(env, job)
        try:
            model = env[job["model_name"]]
        except KeyError:
            _debug.logic(
                "job.terminal",
                job=job["id"],
                reason="model_missing",
                model=job["model_name"],
            )
            raise TerminalJobError(
                env._(
                    "Job %(id)s targets model %(model)s, which no longer exists "
                    "in this database.",
                    id=job["id"],
                    model=job["model_name"],
                )
            ) from None
        records = model.browse(job["record_ids"] or [])
        if _get_job_config(type(records), job["method_name"]) is None:
            _debug.logic(
                "job.terminal",
                job=job["id"],
                reason="not_job_method",
                method=job["method_name"],
            )
            raise TerminalJobError(
                env._(
                    "Job %(id)s calls %(model)s.%(method)s, which is not "
                    "declared with @api.job.",
                    id=job["id"],
                    model=job["model_name"],
                    method=job["method_name"],
                )
            )
        _debug.pipeline(
            "job.target_resolved",
            job=job["id"],
            model=job["model_name"],
            records=len(records),
            uid=job["user_id"],
        )
        return env, records

    @staticmethod
    def _run_claimed(cr, job: dict[str, Any]) -> None:
        env, records = IrJob._get_claimed_target(cr, job)
        _debug.pipeline(
            "job.started",
            job=job["id"],
            method=job["method_name"],
            retry=job["retry"],
            defer_count=job["defer_count"],
        )
        _logger.info(
            "Job %s: %s%s.%s() starting (retry %s/%s)",
            job["id"],
            job["model_name"],
            job["record_ids"] or "",
            job["method_name"],
            job["retry"],
            job["max_retries"],
        )
        job.pop("defer", None)
        try:
            with _running_job(job):
                getattr(records, job["method_name"])(
                    *(job["args"] or []), **(job["kwargs"] or {})
                )
            env.flush_all()
        except MissingError:
            if records and not records.exists():
                _debug.logic("job.terminal", job=job["id"], reason="records_missing")
                raise TerminalJobError(
                    env._(
                        "Job %(id)s targets %(model)s %(ids)s, and none of those "
                        "records exists any more.",
                        id=job["id"],
                        model=job["model_name"],
                        ids=job["record_ids"],
                    )
                ) from None
            _debug.logic("job.missing_error_reraised", job=job["id"])
            raise
        if defer := job.get("defer"):
            _debug.lifecycle("job_deferred", job=job["id"], seconds=defer["seconds"])
            IrJob._record_deferral(cr, job, defer)
            return
        cr.execute(
            SQL(
                "UPDATE ir_job SET state = 'done',"
                " done_at = (now() AT TIME ZONE 'UTC'),"
                " exc_name = NULL, exc_message = NULL, exc_info = NULL,"
                " write_date = (now() AT TIME ZONE 'UTC')"
                " WHERE id = %s AND state = 'started'",
                job["id"],
            )
        )
        if not cr.rowcount:
            _logger.error(
                "Job %s: completed but its row was no longer 'started'; the"
                " work commits without being marked done and may run again",
                job["id"],
            )
            _debug.logic("job.row_lost", job=job["id"], at="done")
        released = IrJob._release_dependents(cr, job["id"])
        if released:
            _debug.pipeline("job.dependents_released", job=job["id"], count=released)
            IrJob._notify_after_commit(cr)
        _logger.info("Job %s: done", job["id"])
        _debug.lifecycle("job_done", job=job["id"], released_dependents=released)

    @staticmethod
    def _record_deferral(cr, job: dict[str, Any], defer: dict[str, Any]) -> None:
        seconds = defer["seconds"]
        cr.execute(
            SQL(
                """
                UPDATE ir_job
                SET state = CASE WHEN %s > 0 THEN 'scheduled' ELSE 'pending' END,
                    eta = (now() AT TIME ZONE 'UTC') + %s * interval '1 second',
                    defer_count = defer_count + 1,
                    defer_reason = %s,
                    exc_name = NULL, exc_message = NULL, exc_info = NULL,
                    started_at = NULL, worker_ident = NULL,
                    write_date = (now() AT TIME ZONE 'UTC')
                WHERE id = %s AND state = 'started'
                """,
                seconds,
                seconds,
                (defer["reason"] or None) and defer["reason"][:1000],
                job["id"],
            )
        )
        _debug.lifecycle(
            "job.deferral_recorded",
            job=job["id"],
            seconds=seconds,
            state="scheduled" if seconds > 0 else "pending",
            defer_count=job["defer_count"] + 1,
        )
        if not cr.rowcount:
            _logger.error(
                "Job %s: asked to be deferred but its row was no longer"
                " 'started'; the work commits and the job may run again",
                job["id"],
            )
            _debug.logic("job.row_lost", job=job["id"], at="defer")
        _logger.info(
            "Job %s: deferred %ss (%s/%s), %s",
            job["id"],
            seconds,
            job["defer_count"] + 1,
            job["max_defers"],
            defer["reason"] or "no reason given",
        )

    @staticmethod
    def _narrow_company_scope(env, job: dict[str, Any]):
        allowed = (job["context"] or {}).get("allowed_company_ids")
        if not allowed or env.su:
            return env
        available = set(env.user._get_company_ids())
        kept = [company_id for company_id in allowed if company_id in available]
        if kept == list(allowed):
            return env
        _logger.warning(
            "Job %s: dropping %s from its company scope, no longer available to %s",
            job["id"],
            sorted(set(allowed) - available),
            env.user.login,
        )
        _debug.logic(
            "job.company_scope_narrowed",
            job=job["id"],
            requested=len(allowed),
            kept=len(kept),
        )
        context = dict(env.context)
        if kept:
            context["allowed_company_ids"] = kept
        else:
            context.pop("allowed_company_ids", None)
        return api.Environment(env.cr, env.uid, context)

    @classmethod
    def _record_failure(cls, cr, job: dict[str, Any], exc: BaseException) -> None:
        retry = job["retry"]
        exc_info = _format_exception(exc)
        _debug.logic(
            "job.failure_classified",
            job=job["id"],
            retry=retry,
            max_retries=job["max_retries"],
            terminal=isinstance(exc, TerminalJobError),
            retryable=isinstance(exc, RetryableJobError),
            error=type(exc).__name__,
        )
        if retry < job["max_retries"] and not isinstance(exc, TerminalJobError):
            seconds = exc.seconds if isinstance(exc, RetryableJobError) else None
            delay = (
                seconds
                if seconds is not None
                else backoff.get_delay(
                    retry + 1, base=RETRY_BACKOFF_BASE_S, cap=RETRY_BACKOFF_MAX_S
                )
            )
            cr.execute(
                SQL(
                    """
                    UPDATE ir_job
                    SET state = CASE WHEN %s > 0 THEN 'scheduled' ELSE 'pending' END,
                        retry = retry + 1,
                        eta = (now() AT TIME ZONE 'UTC') + %s * interval '1 second',
                        exc_name = %s, exc_message = %s, exc_info = %s,
                        started_at = NULL, worker_ident = NULL,
                        write_date = (now() AT TIME ZONE 'UTC')
                    WHERE id = %s AND state = 'started'
                    """,
                    delay,
                    delay,
                    type(exc).__name__,
                    str(exc)[:1000],
                    exc_info,
                    job["id"],
                )
            )
            _logger.info(
                "Job %s: retry %s/%s in %ss (%s)",
                job["id"],
                retry + 1,
                job["max_retries"],
                delay,
                type(exc).__name__,
            )
            _debug.lifecycle(
                "job_retry_scheduled",
                job=job["id"],
                retry=retry + 1,
                delay=delay,
                error=type(exc).__name__,
            )
        else:
            cr.execute(
                SQL(
                    """
                    UPDATE ir_job
                    SET state = 'failed',
                        done_at = (now() AT TIME ZONE 'UTC'),
                        exc_name = %s, exc_message = %s, exc_info = %s,
                        write_date = (now() AT TIME ZONE 'UTC')
                    WHERE id = %s AND state = 'started'
                    """,
                    type(exc).__name__,
                    str(exc)[:1000],
                    exc_info,
                    job["id"],
                )
            )
            _logger.error(
                "Job %s: failed permanently after %s retries", job["id"], retry
            )
            _debug.lifecycle(
                "job_failed", job=job["id"], retries=retry, error=type(exc).__name__
            )
            IrJob._cancel_dependents(cr, [job["id"]])
            cls._notify_failed(cr, job, exc)

    @staticmethod
    def _notify_failed(cr, job: dict[str, Any], exc: BaseException) -> None:
        pass

    @staticmethod
    def _reap_dead_jobs(cr) -> int:
        cr.execute(
            SQL(
                """
                WITH candidates AS MATERIALIZED (
                    SELECT id, retry < max_retries AS requeue
                    FROM ir_job
                    WHERE state = 'started'
                      AND started_at < (now() AT TIME ZONE 'UTC')
                          - %s * interval '1 second'
                    ORDER BY started_at
                    LIMIT %s
                )
                SELECT id, requeue FROM candidates
                 WHERE pg_try_advisory_xact_lock(%s)
                """,
                DEAD_JOB_GRACE_S,
                REAP_BATCH_SIZE,
                _advisory_key_sql(SQL.identifier("id")),
            )
        )
        rows = cr.fetchall()
        if not rows:
            return 0
        requeue_ids = [job_id for job_id, requeue in rows if requeue]
        fail_ids = [job_id for job_id, requeue in rows if not requeue]
        _debug.logic("reap.classified", candidates=len(rows), requeue=len(requeue_ids))
        reaped = 0
        if requeue_ids:
            cr.execute(
                SQL(
                    "UPDATE ir_job SET state = 'pending',"
                    " retry = retry + 1, started_at = NULL,"
                    " worker_ident = NULL, exc_name = 'WorkerDied',"
                    " exc_message = 'job worker died during execution',"
                    " write_date = (now() AT TIME ZONE 'UTC')"
                    " WHERE id = ANY(%s) AND state = 'started'",
                    requeue_ids,
                )
            )
            reaped += cr.rowcount
        if fail_ids:
            cr.execute(
                SQL(
                    "UPDATE ir_job SET state = 'failed',"
                    " done_at = (now() AT TIME ZONE 'UTC'),"
                    " exc_name = 'WorkerDied',"
                    " exc_message = 'job worker died during execution',"
                    " write_date = (now() AT TIME ZONE 'UTC')"
                    " WHERE id = ANY(%s) AND state = 'started'",
                    fail_ids,
                )
            )
            reaped += cr.rowcount
        if reaped:
            _logger.warning(
                "Reaped %s job(s) from dead workers: %s requeued, %s out of retries",
                reaped,
                len(requeue_ids),
                len(fail_ids),
            )
            _debug.lifecycle(
                "jobs_reaped", requeued=len(requeue_ids), failed=len(fail_ids)
            )
        return reaped

    @staticmethod
    def _release_dependents(cr, job_id: int) -> int:
        cr.execute(
            SQL(
                """
                UPDATE ir_job d
                SET state = %s, write_date = (now() AT TIME ZONE 'UTC')
                WHERE d.state = 'wait_deps'
                  AND d.id IN (SELECT job_id FROM ir_job_dependency
                               WHERE depends_on_id = %s)
                  AND NOT EXISTS (
                      SELECT 1
                      FROM ir_job_dependency dd
                      JOIN ir_job pj ON pj.id = dd.depends_on_id
                      WHERE dd.job_id = d.id AND pj.state != 'done'
                  )
                RETURNING d.state
                """,
                _DUE_STATE_SQL,
                job_id,
            )
        )
        released = sum(1 for (state,) in cr.fetchall() if state == JobState.PENDING)
        _debug.pipeline("dependents.released", job=job_id, pending=released)
        return released

    @staticmethod
    def _cancel_dependents(cr, job_ids: list[int]) -> int:
        cr.execute(
            SQL(
                """
                WITH RECURSIVE dependents AS (
                    SELECT d.job_id FROM ir_job_dependency d
                    WHERE d.depends_on_id = ANY(%s::int[])
                    UNION
                    SELECT d2.job_id FROM ir_job_dependency d2
                    JOIN dependents ON d2.depends_on_id = dependents.job_id
                )
                UPDATE ir_job j
                SET state = 'cancelled',
                    done_at = (now() AT TIME ZONE 'UTC'),
                    exc_name = 'DependencyFailed',
                    exc_message = 'a job this one depends on failed'
                                  ' or was cancelled',
                    write_date = (now() AT TIME ZONE 'UTC')
                WHERE j.id IN (SELECT job_id FROM dependents)
                  AND j.state = 'wait_deps'
                """,
                job_ids,
            )
        )
        if cr.rowcount:
            _logger.info(
                "Cancelled %s dependent job(s) of failed/cancelled %s",
                cr.rowcount,
                job_ids,
            )
            _debug.lifecycle(
                "dependents.cancelled", count=cr.rowcount, parents=len(job_ids)
            )
        return cr.rowcount

    @staticmethod
    def _release_ready_dependents(cr) -> None:
        cr.execute(
            SQL(
                """
            UPDATE ir_job d
            SET state = %s, write_date = (now() AT TIME ZONE 'UTC')
            WHERE d.state = 'wait_deps'
              AND NOT EXISTS (
                  SELECT 1
                  FROM ir_job_dependency dd
                  JOIN ir_job pj ON pj.id = dd.depends_on_id
                  WHERE dd.job_id = d.id AND pj.state != 'done'
              )
            """,
                _DUE_STATE_SQL,
            )
        )
        promoted = cr.rowcount
        cr.execute(
            "SELECT DISTINCT d.depends_on_id FROM ir_job_dependency d"
            " JOIN ir_job pj ON pj.id = d.depends_on_id"
            " JOIN ir_job cj ON cj.id = d.job_id"
            " WHERE pj.state IN ('failed', 'cancelled')"
            " AND cj.state = 'wait_deps'"
        )
        dead = [r[0] for r in cr.fetchall()]
        _debug.lifecycle(
            "maintenance.dependents_swept", promoted=promoted, dead_parents=len(dead)
        )
        if dead:
            IrJob._cancel_dependents(cr, dead)
        if promoted:
            _logger.info("Promoted %s job(s) whose dependencies completed", promoted)

    @api.autovacuum
    def _gc_jobs(self) -> tuple[int, bool]:
        now = self.env.cr.now()
        domain = [
            "|",
            "&",
            ("state", "in", (JobState.DONE, JobState.CANCELLED)),
            ("done_at", "<", now - DONE_RETENTION),
            "&",
            ("state", "=", JobState.FAILED),
            ("done_at", "<", now - FAILED_RETENTION),
        ]
        records = self.sudo().search(domain, limit=GC_UNLINK_LIMIT)
        records.unlink()
        _debug.lifecycle(
            "gc_jobs", count=len(records), more=len(records) == GC_UNLINK_LIMIT
        )
        return len(records), len(records) == GC_UNLINK_LIMIT

    def write(self, vals: dict[str, Any]) -> bool:
        _debug.lifecycle("write", count=len(self), fields=list(vals))
        result = super().write(vals)
        if "eta" in vals and "state" not in vals:
            _debug.logic("write.eta_realigns_state", count=len(self))
            self._align_state_with_eta()
        return result

    def _align_state_with_eta(self) -> None:
        now = self._get_clock_timestamp()
        queued = self.filtered(lambda job: job.state in RUNNABLE_STATES)
        due = queued.filtered(lambda job: not job.eta or job.eta <= now)
        if promote := due.filtered(lambda job: job.state != JobState.PENDING):
            _debug.lifecycle("eta.promoted", count=len(promote))
            promote.write({"state": JobState.PENDING})
            self._notify_after_commit(self.env.cr)
        if postpone := (queued - due).filtered(
            lambda job: job.state != JobState.SCHEDULED
        ):
            _debug.lifecycle("eta.postponed", count=len(postpone))
            postpone.write({"state": JobState.SCHEDULED})

    @api.depends("name", "model_name", "method_name")
    def _compute_display_name(self) -> None:
        for job in self:
            job.display_name = (
                job.name or f"{job.model_name}.{job.method_name} (#{job.id})"
            )

    def action_run_now(self) -> None:
        self.check_singleton()
        self.browse().check_access("write")
        self.env.flush_all()
        cr = self.env.cr
        with _job_session_lock(cr, self.id, blocking=False) as acquired:
            if not acquired:
                _debug.logic("run_now.refused", job=self.id, reason="already_running")
                raise UserError(self.env._("This job is already running."))
            try:
                self._run_now_claimed(cr)
            finally:
                self.invalidate_recordset()

    def _run_now_claimed(self, cr) -> None:
        cr.execute(
            SQL(
                """
                UPDATE ir_job
                SET state = 'started',
                    started_at = (now() AT TIME ZONE 'UTC'),
                    worker_ident = %s,
                    write_date = (now() AT TIME ZONE 'UTC')
                WHERE id = %s AND state IN %s
                RETURNING %s
                """,
                f"manual:{self.env.uid}",
                self.id,
                tuple(RUNNABLE_STATES),
                CLAIMED_COLUMNS,
            )
        )
        row = cr.fetchone()
        if row is None:
            _debug.logic("run_now.refused", job=self.id, reason="not_queued")
            raise UserError(self.env._("Only a queued job can be run manually."))
        job = dict(zip([d.name for d in cr.description], row, strict=True))
        _debug.lifecycle("run_now.claimed", job=self.id, uid=self.env.uid)
        self.invalidate_recordset()
        type(self)._run_claimed(cr, job)

    def action_requeue(self) -> None:
        self.browse().check_access("write")
        for job in self:
            if job.state not in REQUEUABLE_STATES:
                _debug.logic("requeue.refused", job=job.id, state=job.state)
                raise UserError(
                    self.env._("Only failed or cancelled jobs can be requeued.")
                )
        cleared = {
            "retry": 0,
            "defer_count": 0,
            "defer_reason": False,
            "eta": False,
            "done_at": False,
            "started_at": False,
            "worker_ident": False,
            "exc_name": False,
            "exc_message": False,
            "exc_info": False,
        }
        waiting = self.filtered(
            lambda job: any(dep.state != JobState.DONE for dep in job.depends_on_ids)
        )
        _debug.lifecycle("requeued", count=len(self), waiting=len(waiting))
        if waiting:
            waiting.sudo().write({"state": JobState.WAIT_DEPS, **cleared})
        if runnable := self - waiting:
            runnable.sudo().write({"state": JobState.PENDING, **cleared})
            self._notify_after_commit(self.env.cr)

    def action_cancel(self) -> None:
        self.browse().check_access("write")
        for job in self:
            if job.state not in CANCELLABLE_STATES:
                _debug.logic("cancel.refused", job=job.id, state=job.state)
                raise UserError(
                    self.env._("Only jobs that have not started yet can be cancelled.")
                )
        self.sudo().write({"state": JobState.CANCELLED, "done_at": self.env.cr.now()})
        _debug.lifecycle("cancelled", count=len(self))
        self.env.flush_all()
        type(self)._cancel_dependents(self.env.cr, self.ids)
