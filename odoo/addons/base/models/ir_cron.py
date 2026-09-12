from __future__ import annotations

import contextvars
import copy
import logging
import math
import os
import threading
import time
import typing
from datetime import datetime, timedelta, UTC

import psycopg2
import psycopg2.errors
from dateutil.relativedelta import relativedelta

from odoo import api, fields, models, sql_db
from odoo.exceptions import ConcurrencyError, LockError, UserError
from odoo.http.dispatcher import serialize_exception
from odoo.modules import Manifest
from odoo.sql_db import PG_CONCURRENCY_EXCEPTIONS_TO_RETRY
from odoo.tools import SQL, config
from odoo.tools.constants import GC_UNLINK_LIMIT

if typing.TYPE_CHECKING:
    from collections.abc import Iterable

    from odoo.sql_db import BaseCursor

_logger = logging.getLogger(__name__)

BASE_VERSION = Manifest.for_addon('base')['version']
MAX_FAIL_TIME = timedelta(hours=5)  # chosen with a fair roll of the dice
MIN_TIME_PER_JOB = 120  # seconds
CONSECUTIVE_TIMEOUT_FOR_FAILURE = 3
MIN_FAILURE_COUNT_BEFORE_DEACTIVATION = 5
MIN_DELTA_BEFORE_DEACTIVATION = timedelta(days=7)
# crons must satisfy both minimum thresholds before deactivation

# custom function to call instead of default PostgreSQL's `pg_notify`
ODOO_NOTIFY_FUNCTION = os.getenv('ODOO_NOTIFY_FUNCTION', 'pg_notify')


class BadVersion(Exception):
    pass


class BadModuleState(Exception):
    pass


_intervalTypes = {
    'days': lambda interval: relativedelta(days=interval),
    'hours': lambda interval: relativedelta(hours=interval),
    'weeks': lambda interval: relativedelta(days=7 * interval),
    'months': lambda interval: relativedelta(months=interval),
    'minutes': lambda interval: relativedelta(minutes=interval),
}


class ListLogHandler(logging.Handler):
    def __init__(self, logger, level=logging.NOTSET):
        super().__init__(level)
        self.logger = logger
        self.list_log_handler = contextvars.ContextVar('list_log_handler', default=None)

    def emit(self, record):
        logs = self.list_log_handler.get(None)
        if logs is None:
            return
        record = copy.copy(record)
        logs.append(record)

    def __enter__(self):
        # set a list in the current context
        logs = []
        self.list_log_handler.set(logs)
        self.logger.addHandler(self)
        return logs

    def __exit__(self, *exc):
        self.logger.removeHandler(self)


class IrCron(models.Model):
    """ Model describing cron jobs (also called actions or tasks).
    """

    # TODO: perhaps in the future we could consider a flag on ir.cron jobs
    # that would cause database wake-up even if the database has not been
    # loaded yet or was already unloaded (e.g. 'force_db_wakeup' or something)
    # See also odoo.cron
    _name = 'ir.cron'
    _order = 'cron_name, id'
    _description = 'Scheduled Action'
    _allow_sudo_commands = False

    _inherits = {'ir.actions.server': 'ir_actions_server_id'}

    ir_actions_server_id = fields.Many2one(
        'ir.actions.server', 'Server action', index=True,
        delegate=True, ondelete='restrict', required=True)
    cron_name = fields.Char('Name', compute='_compute_cron_name', store=True)
    user_id = fields.Many2one('res.users', string='Scheduler User', default=lambda self: self.env.user, required=True)
    active = fields.Boolean(default=True)
    interval_number = fields.Integer(default=1, help="Repeat every x.", required=True, aggregator='avg')
    interval_type = fields.Selection([('minutes', 'Minutes'),
                                      ('hours', 'Hours'),
                                      ('days', 'Days'),
                                      ('weeks', 'Weeks'),
                                      ('months', 'Months')], string='Interval Unit', default='months', required=True)
    nextcall = fields.Datetime(string='Next Execution Date', required=True, default=fields.Datetime.now, help="Next planned execution date for this job.")
    lastcall = fields.Datetime(string='Last Execution Date', help="Previous time the cron ran successfully, provided to the job through the context on the `lastcall` key")
    priority = fields.Integer(default=5, aggregator=None, help='The priority of the job, as an integer: 0 means higher priority, 10 means lower priority.')
    failure_count = fields.Integer(default=0, help="The number of consecutive failures of this job. It is automatically reset on success.")
    first_failure_date = fields.Datetime(string='First Failure Date', help="The first time the cron failed. It is automatically reset on success.")

    _check_strictly_positive_interval = models.Constraint(
        'CHECK(interval_number > 0)',
        "The interval number must be a strictly positive number.",
    )

    @api.depends('ir_actions_server_id.name')
    def _compute_cron_name(self):
        for cron in self.with_context(lang='en_US'):
            cron.cron_name = cron.ir_actions_server_id.name

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            vals['usage'] = 'ir_cron'
        if os.getenv('ODOO_NOTIFY_CRON_CHANGES'):
            self.env.cr.postcommit.add(self._notifydb)
        return super().create(vals_list)

    @api.model
    def default_get(self, fields):
        # only 'code' state is supported for cron job so set it as default
        model = self
        if not model.env.context.get('default_state'):
            model = model.with_context(default_state='code')
        return super(IrCron, model).default_get(fields)

    def method_direct_trigger(self):
        """Run the CRON job in the current (HTTP) thread.

        The job is still ran as it would be by the scheduler: a new cursor
        is used for the execution of the job.

        :raises UserError: when the job is already running
        """
        self.ensure_one()
        self.browse().check_access('write')
        # cron will be run in a separate transaction, flush before and
        # invalidate because data will be changed by that transaction
        self.env.invalidate_all(flush=True)
        cron_cr = self.env.cr
        job = self._acquire_one_job(cron_cr, self.id, include_not_ready=True)
        if not job:
            raise UserError(self.env._("Job '%s' already executing", self.name))

        with ListLogHandler(_logger, logging.ERROR) as capture:
            limit = config['limit_time_real']
            if limit > 0:
                # halve the available hard limit
                end_time = time.monotonic() + limit / 2
            else:
                end_time = 0.0
            self._process_job(cron_cr, job, end_time=end_time)
        if log_record := next((lr for lr in capture if getattr(lr, 'exc_info', None)), None):
            _exc_type, exception, _traceback = log_record.exc_info
            e = RuntimeError()
            e.__cause__ = exception
            error = {
                'code': 0,  # we don't care of this code
                'message': "Odoo Server Error",
                'data': serialize_exception(e),
            }
            return {
                'type': 'ir.actions.client',
                'tag': 'display_exception',
                'params': error,
            }
        return True

    @staticmethod
    def _process_jobs(db_name: str) -> None:
        """ Execute every job ready to be run on this database. """
        try:
            db = sql_db.db_connect(db_name)
            threading.current_thread().dbname = db_name
            with db.cursor() as cron_cr:
                cls = IrCron
                cls._check_version(cron_cr)
                jobs = cls._get_all_ready_jobs(cron_cr)
                if not jobs:
                    return
                cls._check_modules_state(cron_cr, jobs)
                cls._process_jobs_loop(cron_cr, job_ids=[job['id'] for job in jobs])
        except BadVersion:
            _logger.warning('Skipping database %s as its base version is not %s.', db_name, BASE_VERSION)
        except BadModuleState:
            _logger.warning('Skipping database %s because of modules to install/upgrade/remove.', db_name)
        except psycopg2.errors.UndefinedTable:
            # The table ir_cron does not exist; this is probably not an OpenERP database.
            _logger.warning('Tried to poll an undefined table on database %s.', db_name)
        except psycopg2.ProgrammingError:
            raise
        except Exception:
            _logger.warning('Exception in cron:', exc_info=True)
        finally:
            if hasattr(threading.current_thread(), 'dbname'):
                del threading.current_thread().dbname

    @staticmethod
    def _process_jobs_loop(cron_cr: BaseCursor, *, job_ids: Iterable[int] = ()) -> None:
        """ Process ready jobs to run on this database.

        The `cron_cr` is used to lock the currently processed job and relased
        by committing after each job.
        """
        # find when we should stop processing
        end_time = config['limit_time_real_cron']
        if end_time == -1:
            end_time = config['limit_time_real']
        if end_time:
            # halve the hard limit
            end_time = time.monotonic() + end_time / 2
        else:
            end_time = float('+inf')
        for job_id in job_ids:
            try:
                job = IrCron._acquire_one_job(cron_cr, job_id)
            except psycopg2.extensions.TransactionRollbackError:
                cron_cr.rollback()
                _logger.debug("job %s has been processed by another worker, skip", job_id)
                continue
            if not job:
                _logger.debug("job %s is being processed by another worker, skip", job_id)
                continue
            _logger.debug("job %s acquired", job_id)
            # take into account overridings of _process_job() on that database, check_signaling
            registry = api.Environment(cron_cr, api.SUPERUSER_ID, {}).registry
            # run each job in an insolated context from other jobs
            job_end_time = min(end_time, time.monotonic() + MIN_TIME_PER_JOB)
            contextvars.copy_context().run(registry[IrCron._name]._process_job, cron_cr, job, end_time=job_end_time)
            cron_cr.commit()
            _logger.debug("job %s updated and released", job_id)
            if time.monotonic() >= end_time:
                _logger.info("end time reached for processing jobs")
                break

    @staticmethod
    def _check_version(cron_cr):
        """ Ensure the code version matches the database version """
        cron_cr.execute("""
            SELECT latest_version
            FROM ir_module_module
             WHERE name='base'
        """, log_exceptions=False)
        (version,) = cron_cr.fetchone()
        if version is None:
            raise BadModuleState()
        if version != BASE_VERSION:
            raise BadVersion()

    @staticmethod
    def _check_modules_state(cr, jobs):
        """ Ensure no module is installing or upgrading """
        cr.execute("""
            SELECT COUNT(*)
            FROM ir_module_module
            WHERE state LIKE %s
        """, ['to %'])
        (changes,) = cr.fetchone()
        if not changes:
            return

        if not jobs:
            raise BadModuleState()

        # use the max(job['nextcall'], job['write_date']) to avoid the cron
        # reset_module_state for an ongoing module installation process
        # right after installing a module with an old 'nextcall' cron in data
        oldest = min(max(job['nextcall'], job['write_date'] or job['nextcall']) for job in jobs)
        if datetime.now() - oldest < MAX_FAIL_TIME:
            raise BadModuleState()

        # the cron execution failed around MAX_FAIL_TIME * 60 times (1 failure
        # per minute for 5h) in which case we assume that the crons are stuck
        # because the db has zombie states and we force a call to
        # reset_module_states.
        from odoo.modules.loading import reset_modules_state  # noqa: PLC0415
        reset_modules_state(cr)
        cr.commit()

    @staticmethod
    def _get_ready_sql_condition(cr: BaseCursor) -> SQL:
        return SQL("""
            active IS TRUE
            AND (nextcall <= %(now)s
                OR id IN (
                    SELECT cron_id
                    FROM ir_cron_trigger
                    WHERE call_at <= %(now)s
                )
            )
        """, now=cr.now())

    @staticmethod
    def _get_all_ready_jobs(cr: BaseCursor) -> list[dict]:
        """ Return a list of all jobs that are ready to be executed """
        cr.execute(SQL("""
            SELECT *
            FROM ir_cron
            WHERE %s
            ORDER BY failure_count, priority, id
        """, IrCron._get_ready_sql_condition(cr)))
        return cr.dictfetchall()

    @staticmethod
    def _acquire_one_job(cr: BaseCursor, job_id: int, *, include_not_ready: bool = False) -> dict | None:
        """
        Acquire for update the job with id ``job_id``.

        The job should not have been processed yet by the current
        worker. Another worker may process the job again, may that job
        become ready again quickly enough (e.g. self-triggering, high
        frequency, or partially done jobs).

        Note: It is possible that this function raises a
              ``psycopg2.errors.SerializationFailure`` in case the job
              has been processed in another worker. In such case it is
              advised to roll back the transaction and to go on with the
              other jobs.
        """

        # The query must make sure that (i) two cron workers cannot
        # process a given job at a same time. The query must also make
        # sure that (ii) a job already processed in another worker
        # should not be processed again by this one (or at least not
        # before the job becomes ready again).
        #
        # (i) is implemented via `FOR NO KEY UPDATE SKIP LOCKED`, each
        # worker just acquire one available job at a time and lock it so
        # the other workers don't select it too.
        # (ii) is implemented via the `WHERE` statement, when a job has
        # been processed and is fully done, its nextcall is updated to a
        # date in the future and the optional triggers are removed. In
        # case a job has only been partially done, the job is left ready
        # to be acquired again by another cron worker.
        #
        # An `UPDATE` lock type is the strongest row lock, it conflicts
        # with ALL other lock types. Among them the `KEY SHARE` row lock
        # which is implicitly acquired by foreign keys to prevent the
        # referenced record from being removed while in use. Because we
        # never delete acquired cron jobs, foreign keys are safe to
        # concurrently reference cron jobs. Hence, the `NO KEY UPDATE`
        # row lock is used, it is a weaker lock that does conflict with
        # everything BUT `KEY SHARE`.
        #
        # Learn more: https://www.postgresql.org/docs/current/explicit-locking.html#LOCKING-ROWS

        where_clause = SQL("id = %s", job_id)
        if not include_not_ready:
            where_clause = SQL("%s AND %s", where_clause, IrCron._get_ready_sql_condition(cr))
        query = SQL("""
            WITH last_cron_progress AS (
                SELECT id as progress_id, cron_id, timed_out_counter, done, remaining
                FROM ir_cron_progress
                WHERE cron_id = %(cron_id)s
                ORDER BY id DESC
                LIMIT 1
            )
            SELECT *
            FROM ir_cron
            LEFT JOIN last_cron_progress lcp ON lcp.cron_id = ir_cron.id
            WHERE %(where)s
            FOR NO KEY UPDATE SKIP LOCKED
        """, cron_id=job_id, where=where_clause)
        try:
            cr.execute(query, log_exceptions=False)
        except psycopg2.extensions.TransactionRollbackError:
            # A serialization error can occur when another cron worker
            # commits the new `nextcall` value of a cron it just ran and
            # that commit occurred just before this query. The error is
            # genuine and the job should be skipped in this cron worker.
            raise
        except Exception as exc:
            _logger.error("bad query: %s\nERROR: %s", query, exc)
            raise

        job = cr.dictfetchone()

        if not job:     # Job is already taken
            return None

        for field_name in ('done', 'remaining', 'timed_out_counter'):
            job[field_name] = job[field_name] or 0
        return job

    def _notify_admin(self, message):
        """
        Notify ``message`` to some administrator.

        The base implementation of this method does nothing. It is
        supposed to be overridden with some actual communication
        mechanism.
        """
        _logger.warning(message)

    @classmethod
    def _process_job(cls, cron_cr: BaseCursor, job, end_time: float = 0.0) -> None:
        """
        Execute the cron's server action in a dedicated transaction.

        In case the previous process actually timed out, the cron's
        server action is not executed and the cron is considered
        ``'failed'``.

        The server action can use the progress API via the method
        :meth:`_commit_progress` to report how many records are done
        in each batch.
        Those progress notifications are used to determine the job's
        status and to determine the next time the cron
        will be executed:

        - fully done: the cron is rescheduled later, it'll be
          executed again after its regular time interval or upon a new
          trigger.

        - partially done: the cron is rescheduled ASAP, it'll be
          executed again by this or another cron worker once the other
          ready cron jobs have been executed.

        - failed: the cron is deactivated if it failed too many
          times over a given time span; otherwise it is rescheduled
          later.
        """
        # IMPORTANT: when running, updating of cron should be exclusively
        # done by using direct SQL to avoid any hooks from the ORM
        cron_id = job['id']
        cron_name = job['cron_name']
        IrCron = api.Environment(cron_cr, job['user_id'], {}, su=True)[cls._name]
        now = cron_cr.now().replace(microsecond=0)

        # clear the schedule
        cron_cr.execute("""
            DELETE FROM ir_cron_trigger
            WHERE cron_id = %s
              AND call_at <= %s
        """, (cron_id, now))

        active = job['active']
        success = False
        reschedule_asap = False
        if (
            job['timed_out_counter'] >= CONSECUTIVE_TIMEOUT_FOR_FAILURE
            and not job['done']  # when we progress, we never fail, right?
        ):
            # failed by timeout
            cron_cr.execute("""
                UPDATE ir_cron_progress
                SET timed_out_counter = 0
                WHERE id = %s
            """, (job['progress_id'],))
            _logger.error("Job %r (%s) timed out", cron_name, cron_id)
        else:
            # run the job and check resulting progress
            start_time = time.monotonic()
            if not end_time:
                end_time = start_time + MIN_TIME_PER_JOB
            server_action_id = job['ir_actions_server_id']
            with cls.pool.cursor() as job_cr:
                env = api.Environment(job_cr, job['user_id'], {
                    'lastcall': job['lastcall'],
                    'cron_id': cron_id,
                    'cron_end_time': end_time,
                })

                _logger.info('Job %r (%s) starting', cron_name, cron_id)

                progress = env['ir.cron.progress'].sudo().create([{
                    'cron_id': cron_id,
                    'remaining': 0,
                    'done': 0,
                    # we use timed_out_counter + 1 so that if the current execution
                    # times out, the counter already takes it into account
                    'timed_out_counter': 0 if job['timed_out_counter'] is None else job['timed_out_counter'] + 1,
                }])
                env.cr.commit()
                env = env(context=dict(env.context, ir_cron_progress_id=progress.id))

                _logger.debug(
                    "cron.object.execute(%r, %d, '*', %r, %d)",
                    env.cr.dbname,
                    env.uid,
                    cron_name,
                    server_action_id,
                )
                try:
                    env['ir.actions.server'].browse(server_action_id).run()
                    env.flush_all()
                    env.cr.commit()
                    success = True
                except Exception as ex:
                    env.cr.rollback()
                    _logger.exception('Job %r (%s) server action #%s failed',
                        cron_name, cron_id, server_action_id)
                    if isinstance(ex, (*PG_CONCURRENCY_EXCEPTIONS_TO_RETRY, ConcurrencyError)):
                        reschedule_asap = True

                done, remaining = progress.done, progress.remaining
                if success and remaining and done:
                    # XXX change: when nothing was done, don't do asap
                    # XXX maybe do it later? (_trigger in a few minutes?)
                    reschedule_asap = True
                if success and progress.deactivate:
                    active = False

                _logger.info(
                    'Job %r (%s) %s (done %s; remaining %s; duration %.2fs)',
                    cron_name, cron_id, 'success' if success else 'failed',
                    done, remaining, time.monotonic() - start_time)

                env.cr.execute("""
                    UPDATE ir_cron_progress
                    SET timed_out_counter = 0
                    WHERE id = %s
                """, (progress.id,))

        # update the state of the cron job
        if success:
            # reset failure count and date
            failure_count = 0
            first_failure_date = None
        else:
            # failed: increment failure counter
            # check whether we should deactivate the cron
            failure_count = job['failure_count'] + 1
            first_failure_date = job['first_failure_date'] or now
            if (
                failure_count >= MIN_FAILURE_COUNT_BEFORE_DEACTIVATION
                and first_failure_date + MIN_DELTA_BEFORE_DEACTIVATION < now
            ):
                # too many failures, deactivating the cron and resetting counters
                failure_count = 0
                first_failure_date = None
                active = False
                IrCron._notify_admin(IrCron.env._(
                    "Cron job %(name)s (%(id)s) has been deactivated after failing %(count)s times. "
                    "More information can be found in the server logs around %(time)s.",
                    name=repr(cron_name),
                    id=cron_id,
                    count=MIN_FAILURE_COUNT_BEFORE_DEACTIVATION,
                    time=now,
                ))
            elif (
                # the minimum time has passed, and the fail count is low
                first_failure_date + MIN_DELTA_BEFORE_DEACTIVATION < now
                and MIN_FAILURE_COUNT_BEFORE_DEACTIVATION // 2 <= failure_count <= MIN_FAILURE_COUNT_BEFORE_DEACTIVATION
            ) or (
                # we fail often but we have some time before deactivation
                failure_count > MIN_FAILURE_COUNT_BEFORE_DEACTIVATION
                and first_failure_date + MIN_DELTA_BEFORE_DEACTIVATION / 2 < now
                # throttle: number with 1 digit followed only by 0's
                and len(str(failure_count).rstrip('0')) == 1
            ):
                IrCron._notify_admin(IrCron.env._(
                    "Cron job %(name)s (%(id)s) is failing and will be deactivated if you don't take action. "
                    "More information can be found in the server logs around %(time)s.",
                    name=repr(cron_name),
                    id=cron_id,
                    time=now,
                ))

        # create trigger to reschedule asap
        if reschedule_asap and active:
            _logger.debug('job %r (%s) will execute asap', cron_name, cron_id)
            cron_cr.execute("""
                INSERT INTO ir_cron_trigger(cron_id, call_at)
                VALUES (%s, %s)
            """, (cron_id, now))
            if os.getenv('ODOO_NOTIFY_CRON_CHANGES'):
                cron_cr.postcommit.add(IrCron._notifydb)

        # Use the timezone of the user when adding the interval. When adding a
        # day or more, the user may want to keep the same hour each day.
        # The interval won't be fixed, but the hour will stay the same,
        # even when changing DST.
        nextcall = job['nextcall']
        interval = _intervalTypes[job['interval_type']](job['interval_number'])
        while nextcall <= now:
            nextcall = fields.Datetime.context_timestamp(IrCron, nextcall)
            nextcall += interval
            nextcall = nextcall.astimezone(UTC).replace(tzinfo=None)

        cron_cr.execute("""
            UPDATE ir_cron
            SET failure_count = %s,
                first_failure_date = %s,
                lastcall = %s,
                nextcall = %s,
                active = %s
            WHERE id = %s
        """, [
            failure_count,
            first_failure_date,
            now,
            nextcall,
            active,
            cron_id,
        ])

    def write(self, vals):
        try:
            self.lock_for_update(allow_referencing=True)
        except LockError:
            raise UserError(self.env._(
                "Record cannot be modified right now: "
                "This cron task is currently being executed and may not be modified "
                "Please try again in a few minutes"
            )) from None
        if ('nextcall' in vals or vals.get('active')) and os.getenv('ODOO_NOTIFY_CRON_CHANGES'):
            self.env.cr.postcommit.add(self._notifydb)
        return super().write(vals)

    @api.ondelete(at_uninstall=False)
    def _unlink_unless_running(self):
        try:
            self.lock_for_update()
        except LockError:
            raise UserError(self.env._(
                "Record cannot be modified right now: "
                "This cron task is currently being executed and may not be modified "
                "Please try again in a few minutes"
            )) from None

    @api.model
    def toggle(self, model, domain):
        # Prevent deactivated cron jobs from being re-enabled through side effects on
        # neutralized databases.
        if self.env['ir.config_parameter'].sudo().get_bool('database.is_neutralized'):
            return

        active = bool(self.env[model].search_count(domain))
        try:
            self.lock_for_update(allow_referencing=True)
        except LockError:
            return
        self.write({'active': active})

    def _trigger(self, at: datetime | Iterable[datetime] | None = None, *, coalesce: int = 0):
        """
        Schedule a cron job to be executed soon independently of its
        ``nextcall`` field value.

        By default, the cron is scheduled to be executed the next time
        the cron worker wakes up, but the optional `at` argument may be
        given to delay the execution later, with a precision down to 1
        minute.

        The method may be called with a datetime or an iterable of
        datetime. The actual implementation is in :meth:`~._trigger_list`,
        which is the recommended method for overrides.

        :param at:
            When to execute the cron, at one or several moments in time
            instead of as soon as possible.
        :param coalesce: coalescing window, in minutes, every trigger
            is shifted to the end of the window, this allows limiting
            the number or frequency of wakeups for less pressing triggers
        :return: the created triggers records
        """
        if at is None:
            at_list = [fields.Datetime.now()]
        elif isinstance(at, datetime):
            at_list = [at]
        else:
            at_list = list(at)
            assert all(isinstance(at, datetime) for at in at_list)

        if coalesce:
            factor = coalesce * 60
            at_list = [
                datetime.fromtimestamp(
                    math.ceil(dt.timestamp() / factor) * factor,
                )
                for dt in at_list
            ]
        return self._trigger_list(at_list)

    def _trigger_list(self, at_list: list[datetime]):
        """
        Implementation of :meth:`~._trigger`.

        :param at_list: Execute the cron later, at precise moments in time.
        :return: the created triggers records
        """
        self.ensure_one()
        now = fields.Datetime.now()

        if not self.sudo().active:
            # skip triggers that would be ignored
            at_list = [at for at in at_list if at > now]

        if not at_list:
            return self.env['ir.cron.trigger']

        triggers = self.env['ir.cron.trigger'].sudo().create([
            {'cron_id': self.id, 'call_at': at}
            for at in at_list
        ])
        if _logger.isEnabledFor(logging.DEBUG):
            ats = ', '.join(map(str, at_list))
            _logger.debug('Job %r (%s) will execute at %s', self.sudo().name, self.id, ats)

        if min(at_list) <= now or os.getenv('ODOO_NOTIFY_CRON_CHANGES'):
            self.env.cr.postcommit.add(self._notifydb)
        return triggers

    @api.model
    def _notifydb(self):
        """ Wake up the cron workers
        The ODOO_NOTIFY_CRON_CHANGES environment variable allows to force the notifydb on both
        IrCron modification and on trigger creation (regardless of call_at)
        """
        with sql_db.db_connect(config['db_system']).cursor() as cr:
            cr.execute(SQL("SELECT %s('cron_trigger', %s)", SQL.identifier(ODOO_NOTIFY_FUNCTION), self.env.cr.dbname))
        _logger.debug("cron workers notified")

    @api.model
    def _commit_progress(
        self,
        processed: int = 0,
        *,
        remaining: int | None = None,
        deactivate: bool = False,
    ) -> float:
        """
        Commit and log progress for the batch from a cron function.

        The number of items processed is added to the current done count.
        If you don't specify a remaining count, the number of items processed
        is subtracted from the existing remaining count.

        If called from outside the cron job, the progress function call will
        just commit.

        :param processed: number of processed items in this step
        :param remaining: set the remaining count to the given count
        :param deactivate: deactivate the cron after running it
        :return: remaining time (seconds) for the cron run
        """
        # Typical use case:
        # https://www.odoo.com/documentation/latest/developer/reference/backend/actions.html#writing-cron-functions
        ctx = self.env.context
        progress = self.env['ir.cron.progress'].sudo().browse(ctx.get('ir_cron_progress_id'))
        if not progress:
            # not called during a cron, just commit
            self.env.cr.commit()
            return float('inf')
        assert processed >= 0, 'processed must be positive'
        assert (remaining or 0) >= 0, "remaining must be positive"
        assert progress.cron_id.id == ctx.get('cron_id'), "Progress on the wrong cron_id"
        if remaining is None:
            remaining = max(progress.remaining - processed, 0)
        done = progress.done + processed
        vals = {
            'remaining': remaining,
            'done': done,
        }
        if deactivate:
            vals['deactivate'] = True
        progress.write(vals)
        self.env.cr.commit()
        return max(ctx.get('cron_end_time', float('inf')) - time.monotonic(), 0)

    @api.model
    def _rollback_progress(self) -> None:
        """The rollback with the same logic as the commit for cron jobs."""
        self.env.cr.rollback()

    def action_open_parent_action(self):
        return self.ir_actions_server_id.action_open_parent_action()

    def action_open_scheduled_action(self):
        return self.ir_actions_server_id.action_open_scheduled_action()


class IrCronTrigger(models.Model):
    _name = 'ir.cron.trigger'
    _description = 'Triggered Action'
    _rec_name = 'cron_id'
    _allow_sudo_commands = False

    cron_id = fields.Many2one("ir.cron", index=True, required=True, ondelete="cascade")
    call_at = fields.Datetime(index=True, required=True)

    @api.autovacuum
    def _gc_cron_triggers(self):
        # active cron jobs are cleared when the job starts
        domain = [
            ('call_at', '<', datetime.now() + relativedelta(weeks=-1)),
            ('cron_id.active', '=', False),
        ]
        records = self.search(domain, limit=GC_UNLINK_LIMIT)
        records.unlink()
        return len(records), len(records) == GC_UNLINK_LIMIT  # done, remaining


class IrCronProgress(models.Model):
    _name = 'ir.cron.progress'
    _description = 'Progress of Scheduled Action'
    _rec_name = 'cron_id'

    cron_id = fields.Many2one("ir.cron", required=True, index=True, ondelete='cascade')
    remaining = fields.Integer(default=0)
    done = fields.Integer(default=0)
    deactivate = fields.Boolean()
    timed_out_counter = fields.Integer(default=0)

    _deactivate_idx = models.Index("(cron_id, create_date) WHERE deactivate IS TRUE")

    @api.autovacuum
    def _gc_cron_progress(self):
        records = self.search([('create_date', '<', datetime.now() - relativedelta(weeks=1))], limit=GC_UNLINK_LIMIT)
        records.unlink()
        return len(records), len(records) == GC_UNLINK_LIMIT  # done, remaining
