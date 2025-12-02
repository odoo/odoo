from __future__ import annotations

import logging
import threading
import time
import os
import psycopg2
import psycopg2.errors
import typing
from datetime import datetime, timedelta, timezone
from dateutil.relativedelta import relativedelta

from odoo import api, fields, models, sql_db
from odoo.exceptions import LockError, UserError
from odoo.modules import Manifest
from odoo.modules.registry import Registry
from odoo.tools import SQL
from odoo.tools.constants import GC_UNLINK_LIMIT

if typing.TYPE_CHECKING:
    from collections.abc import Iterable
    from odoo.sql_db import BaseCursor

_logger = logging.getLogger(__name__)

BASE_VERSION = Manifest.for_addon('base')['version']
MAX_FAIL_TIME = timedelta(hours=5)  # chosen with a fair roll of the dice
MIN_RUNS_PER_JOB = 10
MIN_TIME_PER_JOB = 10  # seconds
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


class CompletionStatus:  # inherit from enum.StrEnum in 3.11
    FULLY_DONE = 'fully done'
    PARTIALLY_DONE = 'partially done'
    FAILED = 'failed'


class IrCron(models.Model):
    """ Model describing cron jobs (also called actions or tasks).
    """

    # TODO: perhaps in the future we could consider a flag on ir.cron jobs
    # that would cause database wake-up even if the database has not been
    # loaded yet or was already unloaded (e.g. 'force_db_wakeup' or something)
    # See also odoo.cron
    _name = 'ir.cron'
    _order = 'cron_name, id'
    _description = 'Scheduled Actions'
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
        self._process_job(cron_cr, job)
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
    def _process_jobs_loop(cron_cr: BaseCursor, *, job_ids: Iterable[int] = ()):
        """ Process ready jobs to run on this database.

        The `cron_cr` is used to lock the currently processed job and relased
        by committing after each job.
        """
        db_name = cron_cr.dbname
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
            # take into account overridings of _process_job() on that database
            registry = Registry(db_name).check_signaling()
            registry[IrCron._name]._process_job(cron_cr, job)
            cron_cr.commit()
            _logger.debug("job %s updated and released", job_id)

    @staticmethod
    def _check_version(cron_cr):
        """ Ensure the code version matches the database version """
        cron_cr.execute("""
            SELECT latest_version
            FROM ir_module_module
             WHERE name='base'
        """)
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
        reset_modules_state(cr.dbname)

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
            # that commit occured just before this query. The error is
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
    def _process_job(cls, cron_cr: BaseCursor, job) -> None:
        """
        Execute the cron's server action in a dedicated transaction.

        In case the previous process actually timed out, the cron's
        server action is not executed and the cron is considered
        ``'failed'``.

        The server action can use the progress API via the method
        :meth:`_commit_progress` to report how many records are done
        in each batch.
        Those progress notifications are used to determine the job's
        ``CompletionStatus`` and to determine the next time the cron
        will be executed:

        - ``'fully done'``: the cron is rescheduled later, it'll be
          executed again after its regular time interval or upon a new
          trigger.

        - ``'partially done'``: the cron is rescheduled ASAP, it'll be
          executed again by this or another cron worker once the other
          ready cron jobs have been executed.

        - ``'failed'``: the cron is deactivated if it failed too many
          times over a given time span; otherwise it is rescheduled
          later.
        """
        env = api.Environment(cron_cr, job['user_id'], {})
        ir_cron = env[cls._name]

        ir_cron._clear_schedule(job)
        failed_by_timeout = (
            job['timed_out_counter'] >= CONSECUTIVE_TIMEOUT_FOR_FAILURE
            and not job['done']
        )

        if not failed_by_timeout:
            status = cls._run_job(job)
        else:
            status = CompletionStatus.FAILED
            cron_cr.execute("""
                UPDATE ir_cron_progress
                SET timed_out_counter = 0
                WHERE id = %s
            """, (job['progress_id'],))
            _logger.error("Job %r (%s) timed out", job['cron_name'], job['id'])

        ir_cron._update_failure_count(job, status)

        if status in (CompletionStatus.FULLY_DONE, CompletionStatus.FAILED):
            ir_cron._reschedule_later(job)
        elif status == CompletionStatus.PARTIALLY_DONE:
            ir_cron._reschedule_asap(job)
            if os.getenv('ODOO_NOTIFY_CRON_CHANGES'):
                cron_cr.postcommit.add(ir_cron._notifydb)  # See: `_notifydb`
        else:
            raise RuntimeError(f"unreachable {status=}")

    @classmethod
    def _run_job(cls, job) -> CompletionStatus:
        """
        Execute the job's server action multiple times until it
        completes. The completion status is returned.

        It is considered completed when either:

        - the server action doesn't use the progress API, or returned
          and notified that all records has been processed: ``'fully done'``;

        - the server action returned and notified that there are
          remaining records to process, but this cron worker ran this
          server action 10 times already: ``'partially done'``;

        - the server action was able to commit and notify some work done,
          but later crashed due to an exception: ``'partially done'``;

        - the server action failed due to an exception and no progress
          was notified: ``'failed'``.
        """
        timed_out_counter = job['timed_out_counter']

        with cls.pool.cursor() as job_cr:
            start_time = time.monotonic()
            env = api.Environment(job_cr, job['user_id'], {
                'lastcall': job['lastcall'],
                'cron_id': job['id'],
                'cron_end_time': start_time + MIN_TIME_PER_JOB,
            })
            cron = env[cls._name].browse(job['id'])

            status = None
            loop_count = 0
            _logger.info('Job %r (%s) starting', job['cron_name'], job['id'])

            # stop after MIN_RUNS_PER_JOB runs and MIN_TIME_PER_JOB seconds, or
            # upon full completion or failure
            while (
                loop_count < MIN_RUNS_PER_JOB
                or time.monotonic() < env.context['cron_end_time']
            ):
                cron, progress = cron._add_progress(timed_out_counter=timed_out_counter)
                job_cr.commit()

                try:
                    # signaling check and commit is done inside `_callback`
                    cron._callback(job['cron_name'], job['ir_actions_server_id'])
                except Exception:  # noqa: BLE001
                    _logger.exception('Job %r (%s) server action #%s failed',
                        job['cron_name'], job['id'], job['ir_actions_server_id'])
                    if progress.done and progress.remaining:
                        # we do not consider it a failure if some progress has
                        # been committed
                        status = CompletionStatus.PARTIALLY_DONE
                    else:
                        status = CompletionStatus.FAILED
                else:
                    if not progress.remaining:
                        # assume the server action doesn't use the progress API
                        # and that there is nothing left to process
                        status = CompletionStatus.FULLY_DONE
                    else:
                        status = CompletionStatus.PARTIALLY_DONE
                        if not progress.done:
                            break

                    if status == CompletionStatus.FULLY_DONE and progress.deactivate:
                        job['active'] = False
                finally:
                    done, remaining = progress.done, progress.remaining
                    loop_count += 1
                    progress.timed_out_counter = 0
                    timed_out_counter = 0
                    job_cr.commit()  # ensure we have no leftovers

                    _logger.debug('Job %r (%s) processed %s records, %s records remaining',
                        job['cron_name'], job['id'], done, remaining)

                if status in (CompletionStatus.FULLY_DONE, CompletionStatus.FAILED):
                    break

            _logger.info(
                'Job %r (%s) %s (#loop %s; done %s; remaining %s; duration %.2fs)',
                job['cron_name'], job['id'], status,
                loop_count, done, remaining, time.monotonic() - start_time)

        return status

    @api.model
    def _update_failure_count(self, job: dict, status: CompletionStatus) -> None:
        """
        Update cron ``failure_count`` and ``first_failure_date`` given
        the job's completion status. Deactivate the cron when BOTH the
        counter reaches ``MIN_FAILURE_COUNT_BEFORE_DEACTIVATION`` AND
        the time delta reaches ``MIN_DELTA_BEFORE_DEACTIVATION``.

        On ``'fully done'`` and ``'partially done'``, the counter and
        failure date are reset.

        On ``'failed'`` the counter is increased and the first failure
        date is set if the counter was 0. In case both thresholds are
        reached, ``active`` is set to ``False`` and both values are
        reset.
        """
        if status == CompletionStatus.FAILED:
            now = self.env.cr.now().replace(microsecond=0)
            failure_count = job['failure_count'] + 1
            first_failure_date = job['first_failure_date'] or now
            active = job['active']
            if (
                failure_count >= MIN_FAILURE_COUNT_BEFORE_DEACTIVATION
                and first_failure_date + MIN_DELTA_BEFORE_DEACTIVATION < now
            ):
                failure_count = 0
                first_failure_date = None
                active = False
                self._notify_admin(self.env._(
                    "Cron job %(name)s (%(id)s) has been deactivated after failing %(count)s times. "
                    "More information can be found in the server logs around %(time)s.",
                    name=repr(job['cron_name']),
                    id=job['id'],
                    count=MIN_FAILURE_COUNT_BEFORE_DEACTIVATION,
                    time=now,
                ))
        else:
            failure_count = 0
            first_failure_date = None
            active = job['active']

        self.env.cr.execute("""
            UPDATE ir_cron
            SET failure_count = %s,
                first_failure_date = %s,
                active = %s
            WHERE id = %s
        """, [
            failure_count,
            first_failure_date,
            active,
            job['id'],
        ])

    @api.model
    def _clear_schedule(self, job):
        """Remove triggers for the given job."""
        now = self.env.cr.now().replace(microsecond=0)
        self.env.cr.execute("""
            DELETE FROM ir_cron_trigger
            WHERE cron_id = %s
              AND call_at <= %s
        """, [job['id'], now])

    @api.model
    def _reschedule_later(self, job: dict) -> None:
        """
        Reschedule the job to be executed later, after its regular
        interval or upon a trigger.
        """
        now = self.env.cr.now().replace(microsecond=0)
        nextcall = job['nextcall']
        # Use the timezone of the user when adding the interval. When adding a
        # day or more, the user may want to keep the same hour each day.
        # The interval won't be fixed, but the hour will stay the same,
        # even when changing DST.
        interval = _intervalTypes[job['interval_type']](job['interval_number'])
        while nextcall <= now:
            nextcall = fields.Datetime.context_timestamp(self, nextcall)
            nextcall += interval
            nextcall = nextcall.astimezone(timezone.utc).replace(tzinfo=None)

        self.env.cr.execute("""
            UPDATE ir_cron
            SET nextcall = %s,
                lastcall = %s
            WHERE id = %s
        """, [nextcall, now, job['id']])

    @api.model
    def _reschedule_asap(self, job: dict) -> None:
        """
        Reschedule the job to be executed ASAP, after the other cron
        jobs had a chance to run.
        """
        now = self.env.cr.now().replace(microsecond=0)
        self.env.cr.execute("""
            INSERT INTO ir_cron_trigger(call_at, cron_id)
            VALUES (%s, %s)
        """, [now, job['id']])

    def _callback(self, cron_name, server_action_id):
        """ Run the method associated to a given job. It takes care of logging
        and exception handling. Note that the user running the server action
        is the user calling this method. """
        self.ensure_one()
        try:
            if self.pool != self.pool.check_signaling():
                # the registry has changed, reload self in the new registry
                self.env.transaction.reset()

            _logger.debug(
                "cron.object.execute(%r, %d, '*', %r, %d)",
                self.env.cr.dbname,
                self.env.uid,
                cron_name,
                server_action_id,
            )
            self.env['ir.actions.server'].browse(server_action_id).run()
            self.env.flush_all()
            self.pool.signal_changes()
            self.env.cr.commit()
        except Exception:
            self.pool.reset_changes()
            self.env.cr.rollback()
            raise

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
        if self.env['ir.config_parameter'].sudo().get_param('database.is_neutralized'):
            return True

        active = bool(self.env[model].search_count(domain))
        try:
            self.lock_for_update(allow_referencing=True)
        except LockError:
            return True
        return self.write({'active': active})

    def _trigger(self, at: datetime | Iterable[datetime] | None = None):
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
        :return: the created triggers records
        """
        if at is None:
            at_list = [fields.Datetime.now()]
        elif isinstance(at, datetime):
            at_list = [at]
        else:
            at_list = list(at)
            assert all(isinstance(at, datetime) for at in at_list)

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
        with sql_db.db_connect('postgres').cursor() as cr:
            cr.execute(SQL("SELECT %s('cron_trigger', %s)", SQL.identifier(ODOO_NOTIFY_FUNCTION), self.env.cr.dbname))
        _logger.debug("cron workers notified")

    def _add_progress(self, *, timed_out_counter=None):
        """
        Create a progress record for the given cron and add it to its
        context.

        :param int timed_out_counter: the number of times the cron has
            consecutively timed out
        :return: a pair ``(cron, progress)``, where the progress has
            been injected inside the cron's context
        """
        progress = self.env['ir.cron.progress'].sudo().create([{
            'cron_id': self.id,
            'remaining': 0,
            'done': 0,
            # we use timed_out_counter + 1 so that if the current execution
            # times out, the counter already takes it into account
            'timed_out_counter': 0 if timed_out_counter is None else timed_out_counter + 1,
        }])
        return self.with_context(ir_cron_progress_id=progress.id), progress

    @api.deprecated("Since 19.0, use _commit_progress")
    def _notify_progress(self, *, done: int, remaining: int, deactivate: bool = False):
        """
        Log the progress of the cron job.
        Use ``_commit_progress()`` instead.

        :param int done: the number of tasks already processed
        :param int remaining: the number of tasks left to process
        :param bool deactivate: whether the cron will be deactivated
        """
        if not (progress_id := self.env.context.get('ir_cron_progress_id')):
            return
        if done < 0 or remaining < 0:
            raise ValueError("`done` and `remaining` must be positive integers.")
        progress = self.env['ir.cron.progress'].sudo().browse(progress_id)
        assert progress.cron_id.id == self.env.context.get('cron_id'), "Progress on the wrong cron_id"
        progress.write({
            'remaining': remaining,
            'done': done,
            'deactivate': deactivate,
        })

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

    def action_open_parent_action(self):
        return self.ir_actions_server_id.action_open_parent_action()

    def action_open_scheduled_action(self):
        return self.ir_actions_server_id.action_open_scheduled_action()


class IrCronTrigger(models.Model):
    _name = 'ir.cron.trigger'
    _description = 'Triggered actions'
    _rec_name = 'cron_id'
    _allow_sudo_commands = False

    cron_id = fields.Many2one("ir.cron", index=True, required=True, ondelete="cascade")
    call_at = fields.Datetime(index=True, required=True)

    @api.autovacuum
    def _gc_cron_triggers(self):
        # active cron jobs are cleared by `_clear_schedule` when the job starts
        domain = [
            ('call_at', '<', datetime.now() + relativedelta(weeks=-1)),
            ('cron_id.active', '=', False),
        ]
        records = self.search(domain, limit=GC_UNLINK_LIMIT)
        records.unlink()
        return len(records), len(records) == GC_UNLINK_LIMIT  # done, remaining


class IrCronProgress(models.Model):
    _name = 'ir.cron.progress'
    _description = 'Progress of Scheduled Actions'
    _rec_name = 'cron_id'

    cron_id = fields.Many2one("ir.cron", required=True, index=True, ondelete='cascade')
    remaining = fields.Integer(default=0)
    done = fields.Integer(default=0)
    deactivate = fields.Boolean()
    timed_out_counter = fields.Integer(default=0)

    @api.autovacuum
    def _gc_cron_progress(self):
        records = self.search([('create_date', '<', datetime.now() - relativedelta(weeks=1))], limit=GC_UNLINK_LIMIT)
        records.unlink()
        return len(records), len(records) == GC_UNLINK_LIMIT  # done, remaining
