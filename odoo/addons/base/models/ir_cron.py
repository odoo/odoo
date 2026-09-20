import dataclasses
import logging
import math
import os
import time
import typing
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime, timedelta
from enum import StrEnum
from functools import partial
from itertools import starmap
from typing import Any, Self

import psycopg
import psycopg.errors

from odoo import api, db, fields, models
from odoo.api import SUPERUSER_ID, ValuesType
from odoo.db.errors import PG_RETRY_EXCEPTIONS
from odoo.exceptions import LockError, UserError
from odoo.http import serialize_exception
from odoo.libs.debug_log import DebugLog
from odoo.libs.worker_thread import working_on_database
from odoo.models import GC_UNLINK_LIMIT
from odoo.modules import Manifest
from odoo.modules.loading import reset_modules_state
from odoo.modules.registry import Registry
from odoo.service import get_cron_real_time_budget
from odoo.service.transaction import retrying
from odoo.tools import SQL, str2bool
from odoo.tools.constants import CRON_TRIGGER_CHANNEL
from odoo.tools.date_utils import next_after

if typing.TYPE_CHECKING:
    from collections.abc import Callable, Iterable

    from odoo.db import BaseCursor

_logger = logging.getLogger(__name__)
_debug = DebugLog(__name__)

PG_CONCURRENCY_ERRORS = (
    *PG_RETRY_EXCEPTIONS,
    psycopg.errors.TransactionRollback,
    psycopg.errors.TransactionIntegrityConstraintViolation,
    psycopg.errors.StatementCompletionUnknown,
)

BASE_VERSION = Manifest.for_addon("base")["version"]
MAX_FAIL_TIME = timedelta(hours=5)
MIN_RUNS_PER_JOB = 10
MIN_TIME_PER_JOB = 10
RUN_BUDGET_RATIO = 0.8
CONSECUTIVE_TIMEOUT_FOR_FAILURE = 3
MAX_STALLED_ATTEMPTS_PER_RUN = 3
MIN_FAILURE_COUNT_BEFORE_DEACTIVATION = 5
MIN_DELTA_BEFORE_DEACTIVATION = timedelta(days=7)
TRIGGER_RETENTION_PERIOD = timedelta(weeks=1)
PROGRESS_RETENTION_PERIOD = timedelta(weeks=1)

CRON_ADVISORY_LOCK_NAMESPACE = 0x0DD0C401

SLOW_COMPLETION_WRITE = 5.0

NOTIFY_PENDING_KEY = "ir.cron.notify"

ODOO_NOTIFY_FUNCTION = os.getenv("ODOO_NOTIFY_FUNCTION", "pg_notify")


def is_user_archived(env: api.Environment) -> bool:
    return not env.user.active and env.uid != SUPERUSER_ID


def schedule_notify_after_commit(
    cr: BaseCursor, pending_key: str, notify: Callable[[str], None]
) -> None:
    if cr.postcommit.data.get(pending_key):
        return
    cr.postcommit.data[pending_key] = True
    db_name = cr.dbname
    cr.postcommit.add(lambda: notify(db_name))


NOTIFY_CRON_CHANGES = str2bool(os.getenv("ODOO_NOTIFY_CRON_CHANGES", ""), default=False)


def notify_channel(channel: str, db_name: str) -> None:
    try:
        with db.db_connect("postgres").cursor() as cr:
            cr.execute(
                SQL(
                    "SELECT %s(%s, %s)",
                    SQL.identifier(ODOO_NOTIFY_FUNCTION),
                    channel,
                    db_name,
                )
            )
    except psycopg.Error:
        _logger.warning(
            "Could not notify %s workers (%s); the next cron pass picks the "
            "work up regardless",
            channel,
            db_name,
            exc_info=True,
        )
        return
    _logger.debug("%s workers notified (%s)", channel, db_name)


class BadVersionError(Exception):
    pass


class BadModuleStateError(Exception):
    pass


@dataclasses.dataclass(frozen=True, slots=True)
class ReadyJob:
    id: int
    nextcall: datetime
    write_date: datetime | None


@dataclasses.dataclass(slots=True)
class CronJob:
    id: int
    cron_name: str
    user_id: int
    ir_actions_server_id: int
    active: bool
    nextcall: datetime
    lastcall: datetime | None
    repeat_unit: str
    repeat_interval: int
    failure_count: int
    first_failure_date: datetime | None
    progress_id: int | None
    timed_out_counter: int
    deactivate: bool = False
    run_exception: BaseException | None = None

    COLUMNS: typing.ClassVar[tuple[str, ...]] = (
        "id",
        "cron_name",
        "user_id",
        "ir_actions_server_id",
        "active",
        "nextcall",
        "lastcall",
        "repeat_unit",
        "repeat_interval",
        "failure_count",
        "first_failure_date",
    )
    PROGRESS_COLUMNS: typing.ClassVar[tuple[str, ...]] = (
        "progress_id",
        "timed_out_counter",
    )

    @classmethod
    def from_row(cls, row: dict[str, Any]) -> Self:
        return cls(
            **{name: row[name] for name in cls.COLUMNS},
            progress_id=row["progress_id"],
            timed_out_counter=row["timed_out_counter"] or 0,
        )


class _Watermark:
    __slots__ = ("lowest_remaining", "stalled")

    def __init__(self) -> None:
        self.lowest_remaining: float = math.inf
        self.stalled = 0

    def record_success(self) -> None:
        self.lowest_remaining = math.inf
        self.stalled = 0

    def record_failure(self, remaining: int) -> bool:
        if remaining < self.lowest_remaining:
            self.lowest_remaining = remaining
            self.stalled = 0
        else:
            self.stalled += 1
        return self.stalled >= MAX_STALLED_ATTEMPTS_PER_RUN


@contextmanager
def _job_default_env(env: api.Environment) -> Iterator[None]:
    # A job owns its cursor in production. Under registry test mode it borrows
    # the test's transaction, whose default environment has to survive the job:
    # left in place, every later flush of that test class runs as the job's user.
    transaction = env.transaction
    previous = transaction.default_env
    transaction.default_env = env
    try:
        yield
    finally:
        transaction.default_env = previous


class CompletionStatus(StrEnum):
    FULLY_DONE = "fully done"
    PARTIALLY_DONE = "partially done"
    FAILED = "failed"


class IrCron(models.Model):
    _name = "ir.cron"
    _inherit = ["mixin.recurrence.interval"]
    _order = "cron_name, id"
    _description = "Scheduled Actions"
    _allow_sudo_commands = False

    _inherits = {"ir.actions.server": "ir_actions_server_id"}

    ir_actions_server_id = fields.Many2one(
        comodel_name="ir.actions.server",
        delegate=True,
        string="Server action",
        index=True,
        required=True,
        ondelete="restrict",
    )
    cron_name = fields.Char(
        string="Name",
        compute="_compute_cron_name",
        store=True,
    )
    user_id = fields.Many2one(
        comodel_name="res.users",
        string="Scheduler User",
        default=lambda self: self.env.user,
        required=True,
    )
    active = fields.Boolean(default=True)
    repeat_interval = fields.Integer(
        string="Execute Every",
        required=True,
        aggregator="avg",
        help="Repeat every x.",
    )
    repeat_unit = fields.Selection(
        selection_add=[("minute", "Minutes"), ("hour", "Hours"), ("day",)],
        string="Interval Unit",
        default="month",
        required=True,
        ondelete={"minute": "set default", "hour": "set default"},
    )
    nextcall = fields.Datetime(
        string="Next Execution Date",
        default=fields.Datetime.now,
        required=True,
        help="Next planned execution date for this job.",
    )
    lastcall = fields.Datetime(
        string="Last Execution Date",
        help="Previous time the cron ran to completion (whether it finished or failed), provided to the job through the context on the `lastcall` key",
    )
    priority = fields.Integer(
        default=5,
        aggregator=None,
        help="The priority of the job, as an integer: 0 means higher priority, 10 means lower priority.",
    )
    failure_count = fields.Integer(
        default=0,
        help="The number of consecutive failures of this job. It is automatically reset on success.",
    )
    first_failure_date = fields.Datetime(
        help="The first time the cron failed. It is automatically reset on success."
    )

    _check_strictly_positive_interval = models.Constraint(
        "CHECK(repeat_interval > 0)",
        "The interval number must be a strictly positive number.",
    )

    @api.depends("ir_actions_server_id.name")
    def _compute_cron_name(self) -> None:
        for cron in self.with_context(lang="en_US"):
            cron.cron_name = cron.ir_actions_server_id.name

    @api.model_create_multi
    def create(self, vals_list: list[ValuesType]) -> Self:
        vals_list = [{**vals, "usage": "ir_cron"} for vals in vals_list]
        _debug.lifecycle("create", count=len(vals_list))
        if NOTIFY_CRON_CHANGES:
            self._notify_after_commit(self.env.cr)
        return super().create(vals_list)

    @api.model
    def default_get(self, fields: list[str]) -> ValuesType:
        model = self
        if not model.env.context.get("default_state"):
            model = model.with_context(default_state="code")
        return super(IrCron, model).default_get(fields)

    def method_direct_trigger(self) -> dict[str, Any] | bool:
        self.check_singleton()
        self.check_access("write")
        self.env.invalidate_all(flush=True)
        cron_cr = self.env.cr
        job = self._acquire_job(cron_cr, self.id, include_not_ready=True)
        if not job:
            _debug.logic("direct_trigger_refused", job=self.id, reason="executing")
            raise UserError(self.env._("Job '%s' already executing", self.name))

        _debug.lifecycle("direct_trigger", job=job.id, name=job.cron_name)
        self._run_job(cron_cr, job)
        if exception := job.run_exception:
            _debug.logic(
                "direct_trigger_failed", job=job.id, error=type(exception).__name__
            )
            e = RuntimeError()
            e.__cause__ = exception
            error = {
                "code": 0,
                "message": "Odoo Server Error",
                "data": serialize_exception(e),
            }
            return {
                "type": "ir.actions.client",
                "tag": "display_exception",
                "params": error,
            }
        return True

    @staticmethod
    def _process_jobs(db_name: str) -> None:
        with working_on_database(db_name):
            try:
                db_conn = db.db_connect(db_name)
                with db_conn.cursor() as cron_cr:
                    cls = IrCron
                    cls._check_version(cron_cr)
                    jobs = cls._get_jobs_ready(cron_cr)
                    cls._check_modules_state(cron_cr, jobs)
                    _debug.pipeline("cron_pass", db=db_name, ready=len(jobs))
                    if not jobs:
                        _debug.logic("cron_pass_idle", db=db_name)
                        return
                    cls._run_jobs_until_deadline(
                        cron_cr,
                        job_ids=[job.id for job in jobs],
                        deadline=cls._get_deadline_pass(),
                    )
            except BadVersionError:
                _logger.warning(
                    "Skipping database %s as its base version is not %s.",
                    db_name,
                    BASE_VERSION,
                )
                _debug.logic("cron_pass_skipped", db=db_name, reason="bad_version")
            except BadModuleStateError:
                _logger.warning(
                    "Skipping database %s because of modules to install/upgrade/remove.",
                    db_name,
                )
                _debug.logic("cron_pass_skipped", db=db_name, reason="modules_changing")
            except psycopg.errors.UndefinedTable:
                _logger.warning(
                    "Tried to poll an undefined table on database %s.", db_name
                )
                _debug.logic("cron_pass_skipped", db=db_name, reason="no_table")
            except db.PoolError:
                _logger.info("Skipping database %s: could not connect.", db_name)
                _debug.logic("cron_pass_skipped", db=db_name, reason="pool_error")
            except psycopg.ProgrammingError:
                raise
            except Exception:
                _logger.exception(
                    "Unexpected exception in cron for database %s:", db_name
                )

    @staticmethod
    def _get_deadline_pass() -> float | None:
        return IrCron._get_deadline_run(time.monotonic())

    @staticmethod
    def _run_jobs_until_deadline(
        cron_cr: BaseCursor,
        *,
        job_ids: Iterable[int] = (),
        deadline: float | None = None,
    ) -> bool:
        db_name = cron_cr.dbname
        job_ids = list(job_ids)
        registry = Registry(db_name)
        for index, job_id in enumerate(job_ids):
            if deadline is not None and time.monotonic() >= deadline:
                _logger.warning(
                    "Cron pass on %s yielded on its time budget with %s job(s)"
                    " left to run; notifying",
                    db_name,
                    len(job_ids) - index,
                )
                notify_channel(CRON_TRIGGER_CHANNEL, db_name)
                _debug.pipeline(
                    "cron_pass_yielded", db=db_name, left=len(job_ids) - index
                )
                return True
            registry = registry.check_signaling()
            IrCronModel = registry[IrCron._name]
            _debug.pipeline(
                "cron_pass_job", db=db_name, job=job_id, index=index, of=len(job_ids)
            )
            try:
                job = IrCronModel._acquire_job(cron_cr, job_id)
            except PG_CONCURRENCY_ERRORS:
                cron_cr.rollback()
                _logger.debug(
                    "job %s has been processed by another worker, skip", job_id
                )
                _debug.logic("job_skipped", job=job_id, reason="concurrency_error")
                continue
            if not job:
                _logger.debug(
                    "job %s is being processed by another worker, skip", job_id
                )
                _debug.logic("job_skipped", job=job_id, reason="not_acquired")
                continue
            _logger.debug("job %s acquired", job_id)
            _debug.lifecycle("job_acquired", job=job_id, name=job.cron_name)
            try:
                with _debug.perf("job_run", cr=cron_cr, job=job_id, name=job.cron_name):
                    IrCronModel._run_job(cron_cr, job, deadline=deadline)
                cron_cr.commit()
            except Exception as exc:
                cron_cr.rollback()
                _logger.exception("job %s failed to process, skip", job_id)
                _debug.logic("job_process_failed", job=job_id, error=type(exc).__name__)
                continue
            _logger.debug("job %s updated and released", job_id)
            _debug.lifecycle("job_released", job=job_id)
        _debug.pipeline("cron_pass_done", db=db_name, jobs=len(job_ids))
        return False

    @staticmethod
    def _check_version(cron_cr: BaseCursor) -> None:
        cron_cr.execute("""
            SELECT db_version
            FROM ir_module_module
             WHERE name='base'
        """)
        row = cron_cr.fetchone()
        if row is None or row[0] is None:
            _debug.logic("version_check", db=cron_cr.dbname, reason="no_base_row")
            raise BadModuleStateError
        if row[0] != BASE_VERSION:
            _debug.logic(
                "version_check", db=cron_cr.dbname, reason="mismatch", found=row[0]
            )
            raise BadVersionError

    @staticmethod
    def _is_any_module_changing(cr: BaseCursor) -> bool:
        cr.execute(
            "SELECT EXISTS (SELECT 1 FROM ir_module_module WHERE state LIKE %s)",
            ["to %"],
        )
        return cr.fetchone()[0]

    @staticmethod
    def _check_modules_state(cr: BaseCursor, jobs: list[ReadyJob]) -> None:
        if not IrCron._is_any_module_changing(cr):
            return

        if not jobs:
            _debug.logic("modules_changing", db=cr.dbname, decision="skip_no_jobs")
            raise BadModuleStateError

        oldest = min(max(job.nextcall, job.write_date or job.nextcall) for job in jobs)
        if cr.now() - oldest < MAX_FAIL_TIME:
            _debug.logic("modules_changing", db=cr.dbname, decision="skip_recent")
            raise BadModuleStateError

        _debug.logic("modules_changing", db=cr.dbname, decision="reset_states")

        _logger.warning(
            "Database %s has been mid-install/upgrade for over %s with cron work"
            " waiting; resetting the module states.",
            cr.dbname,
            MAX_FAIL_TIME,
        )
        reset_modules_state(cr.dbname)

    @staticmethod
    def _get_sql_condition_ready(cr: BaseCursor) -> SQL:
        return SQL(
            """
            active IS TRUE
            AND (nextcall <= %(now)s
                OR EXISTS (
                    SELECT 1
                    FROM ir_cron_trigger
                    WHERE ir_cron_trigger.cron_id = ir_cron.id
                      AND call_at <= %(now)s
                )
            )
        """,
            now=cr.now(),
        )

    @staticmethod
    def _get_jobs_ready(cr: BaseCursor) -> list[ReadyJob]:
        cr.execute(
            SQL(
                """
            SELECT id, nextcall, write_date
            FROM ir_cron
            WHERE %s
            ORDER BY failure_count, priority, id
        """,
                IrCron._get_sql_condition_ready(cr),
            )
        )
        ready = list(starmap(ReadyJob, cr.fetchall()))
        _debug.perf.count("jobs_ready_read", db=cr.dbname, count=len(ready))
        return ready

    @staticmethod
    def _acquire_job(
        cr: BaseCursor, job_id: int, *, include_not_ready: bool = False
    ) -> CronJob | None:
        cr.execute(
            SQL(
                "SELECT pg_try_advisory_xact_lock(%s, %s)",
                CRON_ADVISORY_LOCK_NAMESPACE,
                job_id,
            )
        )
        if not cr.fetchone()[0]:
            _debug.logic("job_lock_held", job=job_id)
            return None
        where_clause = SQL("id = %s", job_id)
        if not include_not_ready:
            where_clause = SQL(
                "%s AND %s", where_clause, IrCron._get_sql_condition_ready(cr)
            )
        query = SQL(
            """
            WITH last_cron_progress AS (
                SELECT id AS progress_id, cron_id, timed_out_counter
                FROM ir_cron_progress
                WHERE cron_id = %(cron_id)s
                ORDER BY id DESC
                LIMIT 1
            )
            SELECT %(columns)s, %(progress_columns)s
            FROM ir_cron
            LEFT JOIN last_cron_progress lcp ON lcp.cron_id = ir_cron.id
            WHERE %(where)s
        """,
            cron_id=job_id,
            columns=SQL(", ").join(
                SQL.identifier("ir_cron", name) for name in CronJob.COLUMNS
            ),
            progress_columns=SQL(", ").join(
                SQL.identifier("lcp", name) for name in CronJob.PROGRESS_COLUMNS
            ),
            where=where_clause,
        )
        try:
            cr.execute(query, log_exceptions=False, prepare=False)
        except PG_CONCURRENCY_ERRORS:
            raise
        except psycopg.Error as exc:
            _logger.error("bad query: %s\nERROR: %s", query, exc)
            raise

        row = cr.dictfetchone()
        if _debug.logic.enabled and row is None:
            _debug.logic(
                "job_not_ready", job=job_id, include_not_ready=include_not_ready
            )
        return CronJob.from_row(row) if row else None

    def _notify_admin(self, message: str) -> None:
        _logger.warning(message)

    @classmethod
    def _run_job(
        cls,
        cron_cr: BaseCursor,
        job: CronJob,
        *,
        deadline: float | None = None,
    ) -> None:
        env = api.Environment(cron_cr, job.user_id, {})
        with _job_default_env(env):
            ir_cron = env[cls._name]

            ir_cron._remove_triggers_due(job)
            failed_by_timeout = job.timed_out_counter >= CONSECUTIVE_TIMEOUT_FOR_FAILURE
            _debug.logic(
                "job_run_decision",
                job=job.id,
                timed_out_counter=job.timed_out_counter,
                failed_by_timeout=failed_by_timeout,
            )

            if not failed_by_timeout:
                cls._run_job_within_budget(job, deadline=deadline)
                return

            status = CompletionStatus.FAILED
            cron_cr.execute(
                """
                UPDATE ir_cron_progress
                SET timed_out_counter = 0
                WHERE id = %s
            """,
                (job.progress_id,),
            )
            _logger.error("Job %r (%s) timed out", job.cron_name, job.id)
            cls._apply_job_completion(cron_cr, ir_cron, job, status)

    @classmethod
    def _apply_job_completion(
        cls,
        cr: BaseCursor,
        ir_cron: Self,
        job: CronJob,
        status: CompletionStatus,
    ) -> None:
        vals = ir_cron._prepare_failure_vals(job, status)

        if status in (CompletionStatus.FULLY_DONE, CompletionStatus.FAILED):
            vals |= ir_cron._prepare_reschedule_vals(job)
        elif status == CompletionStatus.PARTIALLY_DONE:
            _debug.pipeline("job_rescheduled_asap", job=job.id)
            ir_cron._reschedule_job_asap(job)
            if NOTIFY_CRON_CHANGES:
                cls._notify_after_commit(cr)
        else:
            raise RuntimeError(f"unreachable {status=}")

        _debug.lifecycle(
            "job_completion",
            job=job.id,
            name=job.cron_name,
            status=str(status),
            nextcall=vals.get("nextcall"),
            active=vals.get("active", job.active),
            failure_count=vals.get("failure_count", job.failure_count),
        )
        ir_cron._write_job_row(job, vals)

    @staticmethod
    def _resolve_completion_status(
        *, success: bool, done: int, remaining: int
    ) -> CompletionStatus | None:
        match (success, bool(done), bool(remaining)):
            case (False, True, True):
                return None
            case (False, _, _):
                return CompletionStatus.FAILED
            case (True, _, False):
                return CompletionStatus.FULLY_DONE
            case (True, False, _):
                return CompletionStatus.PARTIALLY_DONE
            case _:
                return None

    @staticmethod
    def _can_keep_running(
        *,
        status: CompletionStatus | None,
        loop_count: int,
        now: float,
        end_time: float,
        hard_deadline: float | None = None,
    ) -> bool:
        if status is not None:
            return False
        if hard_deadline is not None and loop_count and now >= hard_deadline:
            _debug.logic("job_loop_stopped", reason="hard_deadline", loops=loop_count)
            return False
        keep = loop_count < MIN_RUNS_PER_JOB or now < end_time
        if _debug.logic.enabled and not keep:
            _debug.logic("job_loop_stopped", reason="end_time", loops=loop_count)
        return keep

    @staticmethod
    def _get_deadline_run(start_time: float) -> float | None:
        budget = get_cron_real_time_budget()
        _debug.logic("run_budget", seconds=budget, ratio=RUN_BUDGET_RATIO)
        return start_time + budget * RUN_BUDGET_RATIO if budget else None

    @staticmethod
    def _run_server_action_with_retry(
        cron: Self, job: CronJob, env: api.Environment
    ) -> None:
        retrying(
            partial(cron._run_server_action, job.cron_name, job.ir_actions_server_id),
            env,
        )

    @classmethod
    def _resolve_attempt(
        cls,
        job: CronJob,
        *,
        success: bool,
        done: int,
        remaining: int,
        deactivate: bool,
        loop_count: int,
        progress_watermark: _Watermark,
    ) -> CompletionStatus | None:
        status = cls._resolve_completion_status(
            success=success, done=done, remaining=remaining
        )
        _debug.logic(
            "attempt_resolved",
            job=job.id,
            loop=loop_count,
            success=success,
            done=done,
            remaining=remaining,
            status=str(status) if status else None,
        )
        if success:
            progress_watermark.record_success()
        elif status is None and progress_watermark.record_failure(remaining):
            status = CompletionStatus.FAILED
            _debug.logic("job_stalled", job=job.id, remaining=remaining)
            _logger.error(
                "Job %r (%s) failed %s times running with %s record(s) still"
                " to process and no fewer than before; giving up on this run",
                job.cron_name,
                job.id,
                MAX_STALLED_ATTEMPTS_PER_RUN,
                remaining,
            )
        if status is CompletionStatus.FULLY_DONE and deactivate:
            _debug.lifecycle("job_deactivation_requested", job=job.id)
            job.deactivate = True
        elif status is CompletionStatus.PARTIALLY_DONE and not loop_count:
            _logger.warning("Job %r (%s) processed no record", job.cron_name, job.id)
            _debug.logic("job_no_record_processed", job=job.id)
        return status

    @staticmethod
    def _get_budget(
        start_time: float, deadline: float | None
    ) -> tuple[float, float | None]:
        hard_deadline = (
            deadline if deadline is not None else IrCron._get_deadline_run(start_time)
        )
        end_time = start_time + MIN_TIME_PER_JOB
        if hard_deadline is not None:
            end_time = min(end_time, hard_deadline)
        _debug.logic(
            "job_budget",
            soft=end_time - start_time,
            hard=hard_deadline - start_time if hard_deadline is not None else None,
        )
        return end_time, hard_deadline

    @staticmethod
    def _is_user_archived(job: CronJob, env: api.Environment) -> bool:
        if not is_user_archived(env):
            return False
        _logger.warning(
            "Forbidden server action %r executed while the user %s is archived.",
            job.cron_name,
            env.user.login,
        )
        _debug.logic("job_user_archived", job=job.id, uid=job.user_id)
        return True

    @classmethod
    def _run_job_within_budget(
        cls, job: CronJob, *, deadline: float | None = None
    ) -> CompletionStatus:
        with cls.pool.cursor() as job_cr:
            start_time = time.monotonic()
            end_time, hard_deadline = cls._get_budget(start_time, deadline)
            env = api.Environment(
                job_cr,
                job.user_id,
                {
                    "lastcall": job.lastcall,
                    "cron_id": job.id,
                    "cron_end_time": end_time,
                    "cron_hard_deadline": hard_deadline,
                },
            )
            with _job_default_env(env):
                cron = env[cls._name].browse(job.id)

                _logger.info("Job %r (%s) starting", job.cron_name, job.id)
                status = (
                    CompletionStatus.FAILED if cls._is_user_archived(job, env) else None
                )

                status, loop_count, done_total, remaining = cls._drain_cron_job(
                    cron, job, env, job_cr, hard_deadline, status
                )

                status = status or CompletionStatus.PARTIALLY_DONE
                _logger.info(
                    "Job %r (%s) %s (#loop %s; done %s; remaining %s; duration %.2fs)",
                    job.cron_name,
                    job.id,
                    status,
                    loop_count,
                    done_total,
                    remaining,
                    time.monotonic() - start_time,
                )

                _debug.perf.count(
                    "job_run_summary",
                    job=job.id,
                    status=str(status),
                    loops=loop_count,
                    done=done_total,
                    remaining=remaining,
                    seconds=time.monotonic() - start_time,
                )
                cls._apply_job_completion(job_cr, cron, job, status)

        return status

    @classmethod
    def _drain_cron_job(
        cls,
        cron: Self,
        job: CronJob,
        env: api.Environment,
        job_cr: BaseCursor,
        hard_deadline: float | None,
        status: CompletionStatus | None,
    ) -> tuple[CompletionStatus | None, int, int, int]:
        timed_out_counter = job.timed_out_counter
        loop_count = 0
        watermark = _Watermark()
        progress = None
        done_total, remaining = 0, 0

        while cls._can_keep_running(
            status=status,
            loop_count=loop_count,
            now=time.monotonic(),
            end_time=env.context["cron_end_time"],
            hard_deadline=hard_deadline,
        ):
            if progress is None:
                cron, progress = cron._add_progress(timed_out_counter=timed_out_counter)
                _debug.lifecycle(
                    "progress_opened",
                    job=job.id,
                    progress=progress.id,
                    timed_out_counter=timed_out_counter,
                )
                job_cr.commit()
            done_before = progress.done

            success = False
            try:
                with _debug.perf(
                    "server_action_attempt", cr=job_cr, job=job.id, loop=loop_count
                ):
                    cls._run_server_action_with_retry(cron, job, env)
                success = True
            except Exception as exc:
                _logger.exception(
                    "Job %r (%s) server action #%s failed",
                    job.cron_name,
                    job.id,
                    job.ir_actions_server_id,
                )
                _debug.logic(
                    "server_action_failed",
                    job=job.id,
                    loop=loop_count,
                    error=type(exc).__name__,
                )
                if job.run_exception is None:
                    job.run_exception = exc
            finally:
                done_total, remaining = progress.done, progress.remaining
                status = cls._resolve_attempt(
                    job,
                    success=success,
                    done=done_total - done_before,
                    remaining=remaining,
                    deactivate=progress.deactivate,
                    loop_count=loop_count,
                    progress_watermark=watermark,
                )
                loop_count += 1
                if progress.timed_out_counter:
                    _debug.lifecycle("timed_out_counter_reset", job=job.id)
                    progress.timed_out_counter = 0
                job_cr.commit()

                _logger.debug(
                    "Job %r (%s) processed %s records, %s records remaining",
                    job.cron_name,
                    job.id,
                    done_total,
                    remaining,
                )

        return status, loop_count, done_total, remaining

    @api.model
    def _get_now(self) -> datetime:
        return self.env.cr.now().replace(microsecond=0)

    @api.model
    def _prepare_failure_vals(
        self, job: CronJob, status: CompletionStatus
    ) -> dict[str, Any]:
        if status == CompletionStatus.FAILED:
            now = self._get_now()
            failure_count = job.failure_count + 1
            first_failure_date = job.first_failure_date or now
            active = job.active
            if (
                failure_count >= MIN_FAILURE_COUNT_BEFORE_DEACTIVATION
                and first_failure_date + MIN_DELTA_BEFORE_DEACTIVATION < now
            ):
                failure_count = 0
                first_failure_date = None
                active = False
                _debug.lifecycle(
                    "job_deactivated", job=job.id, failures=job.failure_count + 1
                )
                self._notify_admin(
                    self.env._(
                        "Cron job %(name)s (%(id)s) has been deactivated after failing %(count)s times. "
                        "More information can be found in the server logs around %(time)s.",
                        name=repr(job.cron_name),
                        id=job.id,
                        count=job.failure_count + 1,
                        time=now,
                    )
                )
        else:
            failure_count = 0
            first_failure_date = None
            active = job.active

        if job.deactivate:
            active = False

        if (failure_count, first_failure_date, active) == (
            job.failure_count,
            job.first_failure_date,
            job.active,
        ):
            return {}
        _debug.lifecycle(
            "failure_vals",
            job=job.id,
            status=str(status),
            failure_count=failure_count,
            active=active,
        )
        return {
            "failure_count": failure_count,
            "first_failure_date": first_failure_date,
            "active": active,
        }

    @api.model
    def _remove_triggers_due(self, job: CronJob) -> None:
        now = self.env.cr.now()
        self.env.cr.execute(
            """
            DELETE FROM ir_cron_trigger
            WHERE cron_id = %s
              AND call_at <= %s
        """,
            [job.id, now],
        )
        _debug.lifecycle("triggers_due_removed", job=job.id, count=self.env.cr.rowcount)

    @staticmethod
    def _get_next_call(
        record: models.BaseModel,
        nextcall: datetime,
        now: datetime,
        repeat_unit: str,
        repeat_interval: int,
    ) -> datetime:
        return next_after(nextcall, now, repeat_interval, repeat_unit, record.env.tz)

    @api.model
    def _prepare_reschedule_vals(self, job: CronJob) -> dict[str, Any]:
        now = self._get_now()
        nextcall = self._get_next_call(
            self, job.nextcall, now, job.repeat_unit, job.repeat_interval
        )
        _debug.logic(
            "job_rescheduled",
            job=job.id,
            nextcall=nextcall,
            unit=job.repeat_unit,
            interval=job.repeat_interval,
        )
        return {"nextcall": nextcall, "lastcall": now}

    @api.model
    def _write_job_row(self, job: CronJob, vals: dict[str, Any]) -> None:
        if not vals:
            return
        assignments = SQL(", ").join(
            SQL("%s = %s", SQL.identifier(name), value) for name, value in vals.items()
        )
        started = time.monotonic()
        self.env.cr.execute(
            SQL("UPDATE ir_cron SET %s WHERE id = %s", assignments, job.id)
        )
        waited = time.monotonic() - started
        _debug.perf.count(
            "job_row_written", job=job.id, fields=list(vals), seconds=waited
        )
        if waited > SLOW_COMPLETION_WRITE:
            _logger.warning(
                "cron %s: the completion row took %.1fs to write. A single-row "
                "UPDATE by id does not take that long unless it is waiting on a "
                "lock; check pg_blocking_pids for another cursor holding this "
                "row, and see _acquire_job on why it must not be one.",
                job.id,
                waited,
            )

    @api.model
    def _reschedule_job_asap(self, job: CronJob) -> None:
        now = self._get_now()
        self.env.cr.execute(
            """
            INSERT INTO ir_cron_trigger(call_at, cron_id)
            VALUES (%s, %s)
        """,
            [now, job.id],
        )

    def _run_server_action(self, cron_name: str, server_action_id: int) -> None:
        self.check_singleton()
        try:
            if self.pool is not self.pool.check_signaling(self.env.cr):
                _debug.lifecycle("registry_reloaded", cron=cron_name)
                self.env.transaction.reset()

            _logger.debug(
                "cron.object.execute(%r, %d, '*', %r, %d)",
                self.env.cr.dbname,
                self.env.uid,
                cron_name,
                server_action_id,
            )
            self.env["ir.actions.server"].browse(server_action_id).run()
            self.env.flush_all()
            self.pool.signal_changes()
            self.env.cr.commit()
        except Exception as exc:
            _debug.logic(
                "server_action_rolled_back",
                cron=cron_name,
                action=server_action_id,
                error=type(exc).__name__,
            )
            self.pool.reset_changes()
            self.env.cr.rollback()
            raise

    def _raise_currently_executing(self) -> typing.NoReturn:
        raise UserError(
            self.env._(
                "Record cannot be modified right now: "
                "This cron task is currently being executed and may not be modified "
                "Please try again in a few minutes"
            )
        ) from None

    def _lock_for_update_or_raise(self, *, allow_referencing: bool = False) -> None:
        try:
            self.lock_for_update(allow_referencing=allow_referencing)
        except LockError:
            _debug.logic("lock_refused", records=self, reason="row_locked")
            self._raise_currently_executing()
        for record in self:
            self.env.cr.execute(
                SQL(
                    "SELECT pg_try_advisory_xact_lock(%s, %s)",
                    CRON_ADVISORY_LOCK_NAMESPACE,
                    record.id,
                )
            )
            if not self.env.cr.fetchone()[0]:
                _debug.logic("lock_refused", job=record.id, reason="advisory_held")
                record._raise_currently_executing()

    def write(self, vals: dict[str, Any]) -> bool:
        self._lock_for_update_or_raise(allow_referencing=True)
        _debug.lifecycle("write", count=len(self), fields=list(vals))
        if ("nextcall" in vals or vals.get("active")) and NOTIFY_CRON_CHANGES:
            self._notify_after_commit(self.env.cr)
        return super().write(vals)

    @api.ondelete(at_uninstall=False)
    def _unlink_except_running(self) -> None:
        self._lock_for_update_or_raise()
        _debug.lifecycle("unlink", count=len(self))

    @api.model
    def toggle(self, model: str, domain: list[Any]) -> bool:
        if self.env["ir.config_parameter"].sudo().get_param("database.is_neutralized"):
            _debug.logic("toggle_skipped", reason="neutralized")
            return True

        active = bool(self.env[model].search_count(domain, limit=1))
        _debug.logic("toggle", job=self.id, model=model, active=active)
        try:
            return self.write({"active": active})
        except UserError:
            _debug.logic("toggle_skipped", job=self.id, reason="executing")
            return True

    def _trigger(
        self, at: datetime | Iterable[datetime] | None = None, *, coalesce: int = 0
    ) -> IrCronTrigger:
        self.check_singleton()
        if at is None:
            at_list = [self._get_now()]
        elif isinstance(at, datetime):
            at_list = [at]
        else:
            at_list = list(at)
            if not all(isinstance(item, datetime) for item in at_list):
                raise TypeError("all items in 'at' must be datetime objects")

        if coalesce:
            _debug.logic("trigger_coalesced", job=self.id, minutes=coalesce)
            factor = coalesce * 60
            at_list = [
                datetime.fromtimestamp(
                    math.ceil(dt.replace(tzinfo=UTC).timestamp() / factor) * factor,
                    UTC,
                ).replace(tzinfo=None)
                for dt in at_list
            ]

        return self._add_triggers(at_list)

    def _add_triggers(self, at_list: list[datetime]) -> IrCronTrigger:
        self.check_singleton()
        now = self._get_now()

        if not self.sudo().active:
            _debug.logic("triggers_filtered_inactive", job=self.id)
            at_list = [at for at in at_list if at > now]

        _debug.lifecycle("triggers_added", job=self.id, count=len(at_list))
        if not at_list:
            return self.env["ir.cron.trigger"]

        triggers = (
            self.env["ir.cron.trigger"]
            .sudo()
            .create([{"cron_id": self.id, "call_at": at} for at in at_list])
        )
        if _logger.isEnabledFor(logging.DEBUG):
            ats = ", ".join(map(str, at_list))
            _logger.debug(
                "Job %r (%s) will execute at %s", self.sudo().name, self.id, ats
            )

        if min(at_list) <= now or NOTIFY_CRON_CHANGES:
            _debug.pipeline("trigger_notify_scheduled", job=self.id)
            self._notify_after_commit(self.env.cr)
        return triggers

    @staticmethod
    def _notify_after_commit(cr: BaseCursor) -> None:
        schedule_notify_after_commit(
            cr,
            NOTIFY_PENDING_KEY,
            lambda db_name: notify_channel(CRON_TRIGGER_CHANNEL, db_name),
        )

    def _add_progress(
        self, *, timed_out_counter: int | None = None
    ) -> tuple[Self, IrCronProgress]:
        progress = (
            self.env["ir.cron.progress"]
            .sudo()
            .create(
                [
                    {
                        "cron_id": self.id,
                        "remaining": 0,
                        "done": 0,
                        "timed_out_counter": (
                            0 if timed_out_counter is None else timed_out_counter + 1
                        ),
                    }
                ]
            )
        )
        return self.with_context(ir_cron_progress_id=progress.id), progress

    @api.model
    def _commit_progress(
        self,
        processed: int = 0,
        *,
        remaining: int | None = None,
        deactivate: bool = False,
    ) -> float:
        ctx = self.env.context
        progress = (
            self.env["ir.cron.progress"].sudo().browse(ctx.get("ir_cron_progress_id"))
        )
        if not progress:
            _debug.logic("progress_commit_unscoped", cron=ctx.get("cron_id"))
            self.env.cr.commit()
            return float("inf")
        if processed < 0:
            _debug.logic("progress_rejected", reason="negative_processed")
            raise ValueError("processed must be non-negative")
        if remaining is not None and remaining < 0:
            _debug.logic("progress_rejected", reason="negative_remaining")
            raise ValueError("remaining must be non-negative")
        if progress.cron_id.id != ctx.get("cron_id"):
            _debug.logic("progress_rejected", reason="wrong_cron")
            raise ValueError("Progress on the wrong cron_id")
        if remaining is None:
            remaining = max(progress.remaining - processed, 0)
        done = progress.done + processed
        vals = {
            "remaining": remaining,
            "done": done,
        }
        if deactivate:
            vals["deactivate"] = True
        _debug.pipeline(
            "progress",
            job=ctx.get("cron_id"),
            processed=processed,
            done=done,
            remaining=remaining,
            deactivate=deactivate,
        )
        progress.write(vals)
        self.env.cr.commit()
        return max(ctx.get("cron_end_time", float("inf")) - time.monotonic(), 0)

    def action_view_parent_action(self) -> dict[str, Any]:
        return self.ir_actions_server_id.action_view_parent_action()

    def action_view_scheduled_action(self) -> dict[str, Any]:
        return self.ir_actions_server_id.action_view_scheduled_action()


class IrCronTrigger(models.Model):
    _name = "ir.cron.trigger"
    _description = "Triggered actions"
    _rec_name = "cron_id"
    _allow_sudo_commands = False

    cron_id = fields.Many2one(
        comodel_name="ir.cron",
        required=True,
        ondelete="cascade",
    )
    call_at = fields.Datetime(
        index=True,
        required=True,
    )

    _cron_id_call_at_idx = models.Index("(cron_id, call_at)")

    @api.autovacuum
    def _gc_cron_triggers(self) -> tuple[int, bool]:
        domain = [
            ("call_at", "<", self.env.cr.now() - TRIGGER_RETENTION_PERIOD),
            ("cron_id.active", "=", False),
        ]
        records = self.search(domain, limit=GC_UNLINK_LIMIT)
        records.unlink()
        _debug.lifecycle("gc_triggers", count=len(records))
        return len(records), len(records) == GC_UNLINK_LIMIT


class IrCronProgress(models.Model):
    _name = "ir.cron.progress"
    _description = "Progress of Scheduled Actions"
    _rec_name = "cron_id"
    _allow_sudo_commands = False

    cron_id = fields.Many2one(
        comodel_name="ir.cron",
        index=True,
        required=True,
        ondelete="cascade",
    )
    remaining = fields.Integer(default=0)
    done = fields.Integer(default=0)
    deactivate = fields.Boolean()
    timed_out_counter = fields.Integer(default=0)

    _cron_id_id_idx = models.Index("(cron_id, id DESC)")
    _create_date_idx = models.Index("(create_date)")

    @api.autovacuum
    def _gc_cron_progress(self) -> tuple[int, bool]:
        records = self.search(
            [("create_date", "<", self.env.cr.now() - PROGRESS_RETENTION_PERIOD)],
            limit=GC_UNLINK_LIMIT,
        )
        full_batch = len(records) == GC_UNLINK_LIMIT
        self.env.cr.execute(
            "SELECT max(id) FROM ir_cron_progress"
            " WHERE cron_id = ANY(%s) GROUP BY cron_id",
            [records.cron_id.ids],
        )
        kept = self.browse(row[0] for row in self.env.cr.fetchall())
        _debug.logic("gc_progress_latest_kept", kept=len(kept))
        records -= kept
        records.unlink()
        _debug.lifecycle("gc_progress", count=len(records), full_batch=full_batch)
        return len(records), full_batch
