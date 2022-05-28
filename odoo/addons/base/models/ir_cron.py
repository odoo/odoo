# Part of Odoo. See LICENSE file for full copyright and licensing details.
import logging
import threading
import time
import os
import psycopg2
import pytz
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta

import odoo
from odoo import api, fields, models, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

BASE_VERSION = odoo.modules.load_information_from_description_file('base')['version']
MAX_FAIL_TIME = timedelta(hours=5)  # chosen with a fair roll of the dice


class BadVersion(Exception):
    pass

class BadModuleState(Exception):
    pass


_intervalTypes = {
    'days': lambda interval: relativedelta(days=interval),
    'hours': lambda interval: relativedelta(hours=interval),
    'weeks': lambda interval: relativedelta(days=7*interval),
    'months': lambda interval: relativedelta(months=interval),
    'minutes': lambda interval: relativedelta(minutes=interval),
}


class ir_cron(models.Model):
    """ Model describing cron jobs (also called actions or tasks).
    """

    # TODO: perhaps in the future we could consider a flag on ir.cron jobs
    # that would cause database wake-up even if the database has not been
    # loaded yet or was already unloaded (e.g. 'force_db_wakeup' or something)
    # See also odoo.cron

    _name = "ir.cron"
    _order = 'cron_name'
    _description = 'Scheduled Actions'

    ir_actions_server_id = fields.Many2one(
        'ir.actions.server', 'Server action',
        delegate=True, ondelete='restrict', required=True)
    cron_name = fields.Char('Name', related='ir_actions_server_id.name', store=True, readonly=False)
    user_id = fields.Many2one('res.users', string='Scheduler User', default=lambda self: self.env.user, required=True)
    active = fields.Boolean(default=True)
    interval_number = fields.Integer(default=1, help="Repeat every x.")
    interval_type = fields.Selection([('minutes', 'Minutes'),
                                      ('hours', 'Hours'),
                                      ('days', 'Days'),
                                      ('weeks', 'Weeks'),
                                      ('months', 'Months')], string='Interval Unit', default='months')
    numbercall = fields.Integer(string='Number of Calls', default=1, help='How many times the method is called,\na negative number indicates no limit.')
    doall = fields.Boolean(string='Repeat Missed', help="Specify if missed occurrences should be executed when the server restarts.")
    nextcall = fields.Datetime(string='Next Execution Date', required=True, default=fields.Datetime.now, help="Next planned execution date for this job.")
    lastcall = fields.Datetime(string='Last Execution Date', help="Previous time the cron ran successfully, provided to the job through the context on the `lastcall` key")
    priority = fields.Integer(default=5, help='The priority of the job, as an integer: 0 means higher priority, 10 means lower priority.')

    @api.model
    def create(self, values):
        values['usage'] = 'ir_cron'
        if os.getenv('ODOO_NOTIFY_CRON_CHANGES'):
            self._cr.postcommit.add(self._notifydb)
        return super(ir_cron, self).create(values)

    @api.model
    def default_get(self, fields_list):
        # only 'code' state is supported for cron job so set it as default
        if not self._context.get('default_state'):
            self = self.with_context(default_state='code')
        return super(ir_cron, self).default_get(fields_list)

    def method_direct_trigger(self):
        self.check_access_rights('write')
        for cron in self:
            cron.with_user(cron.user_id).with_context(lastcall=cron.lastcall).ir_actions_server_id.run()
            cron.lastcall = fields.Datetime.now()
        return True

    @classmethod
    def _process_jobs(cls, db_name):
        """ Execute every job ready to be run on this database. """
        try:
            db = odoo.sql_db.db_connect(db_name)
            threading.current_thread().dbname = db_name
            with db.cursor() as cron_cr:
                cls._check_version(cron_cr)
                jobs = cls._get_all_ready_jobs(cron_cr)
                if not jobs:
                    return
                cls._check_modules_state(cron_cr, jobs)

                for job_id in (job['id'] for job in jobs):
                    try:
                        job = cls._acquire_one_job(cron_cr, (job_id,))
                    except psycopg2.extensions.TransactionRollbackError:
                        cron_cr.rollback()
                        _logger.debug("job %s has been processed by another worker, skip", job_id)
                        continue
                    if not job:
                        _logger.debug("another worker is processing job %s, skip", job_id)
                        continue
                    _logger.debug("job %s acquired", job_id)
                    # take into account overridings of _process_job() on that database
                    registry = odoo.registry(db_name)
                    registry[cls._name]._process_job(db, cron_cr, job)
                    _logger.debug("job %s updated and released", job_id)

        except BadVersion:
            _logger.warning('Skipping database %s as its base version is not %s.', db_name, BASE_VERSION)
        except BadModuleState:
            _logger.warning('Skipping database %s because of modules to install/upgrade/remove.', db_name)
        except psycopg2.ProgrammingError as e:
            if e.pgcode == '42P01':
                # Class 42 — Syntax Error or Access Rule Violation; 42P01: undefined_table
                # The table ir_cron does not exist; this is probably not an OpenERP database.
                _logger.warning('Tried to poll an undefined table on database %s.', db_name)
            else:
                raise
        except Exception:
            _logger.warning('Exception in cron:', exc_info=True)
        finally:
            if hasattr(threading.current_thread(), 'dbname'):
                del threading.current_thread().dbname

    @classmethod
    def _check_version(cls, cron_cr):
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

    @classmethod
    def _check_modules_state(cls, cr, jobs):
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

        oldest = min([
            fields.Datetime.from_string(job['nextcall'])
            for job in jobs
        ])
        if datetime.now() - oldest < MAX_FAIL_TIME:
            raise BadModuleState()

        # the cron execution failed around MAX_FAIL_TIME * 60 times (1 failure
        # per minute for 5h) in which case we assume that the crons are stuck
        # because the db has zombie states and we force a call to
        # reset_module_states.
        odoo.modules.reset_modules_state(cr.dbname)

    @classmethod
    def _get_all_ready_jobs(cls, cr):
        """ Return a list of all jobs that are ready to be executed """
        cr.execute("""
            SELECT *
            FROM ir_cron
            WHERE active = true
              AND numbercall != 0
              AND (nextcall <= (now() at time zone 'UTC')
                OR id in (
                    SELECT cron_id
                    FROM ir_cron_trigger
                    WHERE call_at <= (now() at time zone 'UTC')
                )
              )
            ORDER BY priority
        """)
        return cr.dictfetchall()

    @classmethod
    def _acquire_one_job(cls, cr, job_ids):
        """
        Acquire for update one job that is ready from the job_ids tuple.

        The jobs that have already been processed in this worker should
        be excluded from the tuple.

        This function raises a ``psycopg2.errors.SerializationFailure``
        when the ``nextcall`` of one of the job_ids is modified in
        another transaction. You should rollback the transaction and try
        again later.
        """

        # We have to make sure ALL jobs are executed ONLY ONCE no matter
        # how many cron workers may process them. The exlusion mechanism
        # is twofold: (i) prevent parallel processing of the same job,
        # and (ii) prevent re-processing jobs that have been processed
        # already.
        #
        # (i) is implemented via `LIMIT 1 FOR UPDATE SKIP LOCKED`, each
        # worker just acquire one available job at a time and lock it so
        # the other workers don't select it too.
        # (ii) is implemented via the `WHERE` statement, when a job has
        # been processed, its nextcall is updated to a date in the
        # future and the optional triggers are removed.
        #
        # Note about (ii): it is possible that a job becomes available
        # again quickly (e.g. high frequency or self-triggering cron).
        # This function doesn't prevent from acquiring that job multiple
        # times at different moments. This can block a worker on
        # executing a same job in loop. To prevent this problem, the
        # callee is responsible of providing a `job_ids` tuple without
        # the jobs it has executed already.
        #
        # An `UPDATE` lock type is the strongest row lock, it conflicts
        # with ALL other lock types. Among them the `KEY SHARE` row lock
        # which is implicitely aquired by foreign keys to prevent the
        # referenced record from being removed while in use. Because we
        # never delete acquired cron jobs, foreign keys are safe to
        # concurrently reference cron jobs. Hence, the `NO KEY UPDATE`
        # row lock is used, it is a weaker lock that does conflict with
        # everything BUT `KEY SHARE`.
        #
        # Learn more: https://www.postgresql.org/docs/current/explicit-locking.html#LOCKING-ROWS

        cr.execute("""
            SELECT *
            FROM ir_cron
            WHERE active = true
              AND numbercall != 0
              AND (nextcall <= (now() at time zone 'UTC')
                OR EXISTS (
                    SELECT cron_id
                    FROM ir_cron_trigger
                    WHERE call_at <= (now() at time zone 'UTC')
                      AND cron_id = ir_cron.id
                )
              )
              AND id in %s
            ORDER BY priority
            LIMIT 1 FOR NO KEY UPDATE SKIP LOCKED
        """, [job_ids])
        return cr.dictfetchone()

    @classmethod
    def _process_job(cls, db, cron_cr, job):
        """ Execute a cron job and re-schedule a call for later. """

        # Compute how many calls were missed and at what time we should
        # recall the cron next. In the example bellow, we fake a cron
        # with an interval of 30 (starting at 0) that was last executed
        # at 15 and that is executed again at 135.
        #
        #    0          60          120         180
        #  --|-----|-----|-----|-----|-----|-----|----> time
        #    1     2*    *     *     *  3  4
        #
        # 1: lastcall, the last time the cron was executed
        # 2: past_nextcall, the cron nextcall as seen from lastcall
        # *: missed_call, a total of 4 calls are missing
        # 3: now
        # 4: future_nextcall, the cron nextcall as seen from now

        with cls.pool.cursor() as job_cr:
            lastcall = fields.Datetime.to_datetime(job['lastcall'])
            interval = _intervalTypes[job['interval_type']](job['interval_number'])
            env = api.Environment(job_cr, job['user_id'], {'lastcall': lastcall})
            ir_cron = env[cls._name]

            # Use the user's timezone to compare and compute datetimes,
            # otherwise unexpected results may appear. For instance, adding
            # 1 month in UTC to July 1st at midnight in GMT+2 gives July 30
            # instead of August 1st!
            now = fields.Datetime.context_timestamp(ir_cron, datetime.utcnow())
            past_nextcall = fields.Datetime.context_timestamp(
                ir_cron, fields.Datetime.to_datetime(job['nextcall']))

            # Compute how many call were missed
            missed_call = past_nextcall
            missed_call_count = 0
            while missed_call <= now:
                missed_call += interval
                missed_call_count += 1
            future_nextcall = missed_call

            # Compute how many time we should run the cron
            effective_call_count = (
                     1 if not missed_call_count                    # run at least once
                else 1 if not job['doall']                         # run once for all
                else missed_call_count if job['numbercall'] == -1  # run them all
                else min(missed_call_count, job['numbercall'])     # run maximum numbercall times
            )
            call_count_left = max(job['numbercall'] - effective_call_count, -1)

            # The actual cron execution
            for call in range(effective_call_count):
                ir_cron._callback(job['cron_name'], job['ir_actions_server_id'], job['id'])

        # Update the cron with the information computed above
        cron_cr.execute("""
            UPDATE ir_cron
            SET nextcall=%s,
                numbercall=%s,
                lastcall=%s,
                active=%s
            WHERE id=%s
        """, [
            fields.Datetime.to_string(future_nextcall.astimezone(pytz.UTC)),
            call_count_left,
            fields.Datetime.to_string(now.astimezone(pytz.UTC)),
            job['active'] and bool(call_count_left),
            job['id'],
        ])

        cron_cr.execute("""
            DELETE FROM ir_cron_trigger
            WHERE cron_id = %s
              AND call_at < (now() at time zone 'UTC')
        """, [job['id']])

        cron_cr.commit()

    @api.model
    def _callback(self, cron_name, server_action_id, job_id):
        """ Run the method associated to a given job. It takes care of logging
        and exception handling. Note that the user running the server action
        is the user calling this method. """
        try:
            if self.pool != self.pool.check_signaling():
                # the registry has changed, reload self in the new registry
                self.env.reset()
                self = self.env()[self._name]

            log_depth = (None if _logger.isEnabledFor(logging.DEBUG) else 1)
            odoo.netsvc.log(_logger, logging.DEBUG, 'cron.object.execute', (self._cr.dbname, self._uid, '*', cron_name, server_action_id), depth=log_depth)
            start_time = False
            _logger.info('Starting job `%s`.', cron_name)
            if _logger.isEnabledFor(logging.DEBUG):
                start_time = time.time()
            self.env['ir.actions.server'].browse(server_action_id).run()
            _logger.info('Job `%s` done.', cron_name)
            if start_time and _logger.isEnabledFor(logging.DEBUG):
                end_time = time.time()
                _logger.debug('%.3fs (cron %s, server action %d with uid %d)', end_time - start_time, cron_name, server_action_id, self.env.uid)
            self.pool.signal_changes()
        except Exception as e:
            self.pool.reset_changes()
            _logger.exception("Call from cron %s for server action #%s failed in Job #%s",
                              cron_name, server_action_id, job_id)
            self._handle_callback_exception(cron_name, server_action_id, job_id, e)

    @api.model
    def _handle_callback_exception(self, cron_name, server_action_id, job_id, job_exception):
        """ Method called when an exception is raised by a job.

        Simply logs the exception and rollback the transaction. """
        self._cr.rollback()

    def _try_lock(self, lockfk=False):
        """Try to grab a dummy exclusive write-lock to the rows with the given ids,
           to make sure a following write() or unlink() will not block due
           to a process currently executing those cron tasks.

           :param lockfk: acquire a strong row lock which conflicts with
                          the lock aquired by foreign keys when they
                          reference this row.
        """
        row_level_lock = "UPDATE" if lockfk else "NO KEY UPDATE"
        try:
            self._cr.execute(f"""
                SELECT id
                FROM "{self._table}"
                WHERE id IN %s
                FOR {row_level_lock} NOWAIT
            """, [tuple(self.ids)], log_exceptions=False)
        except psycopg2.OperationalError:
            self._cr.rollback()  # early rollback to allow translations to work for the user feedback
            raise UserError(_("Record cannot be modified right now: "
                              "This cron task is currently being executed and may not be modified "
                              "Please try again in a few minutes"))

    def write(self, vals):
        self._try_lock()
        if ('nextcall' in vals or vals.get('active')) and os.getenv('ODOO_NOTIFY_CRON_CHANGES'):
            self._cr.postcommit.add(self._notifydb)
        return super(ir_cron, self).write(vals)

    def unlink(self):
        self._try_lock(lockfk=True)
        return super(ir_cron, self).unlink()

    def try_write(self, values):
        try:
            with self._cr.savepoint():
                self._cr.execute(f"""
                    SELECT id
                    FROM "{self._table}"
                    WHERE id IN %s
                    FOR NO KEY UPDATE NOWAIT
                """, [tuple(self.ids)], log_exceptions=False)
        except psycopg2.OperationalError:
            pass
        else:
            return super(ir_cron, self).write(values)
        return False

    @api.model
    def toggle(self, model, domain):
        # Prevent deactivated cron jobs from being re-enabled through side effects on
        # neutralized databases.
        if self.env['ir.config_parameter'].sudo().get_param('database.is_neutralized'):
            return True

        active = bool(self.env[model].search_count(domain))
        return self.try_write({'active': active})

    @api.model
    def _trigger(self, at=None):
        """
        Schedule a cron job to be executed soon independently of its
        ``nextcall`` field value.

        By default the cron is scheduled to be executed in the next batch but
        the optional `at` argument may be given to delay the execution later
        with a precision down to 1 minute.

        The method may be called with a datetime or an iterable of datetime.
        The actual implementation is in :meth:`~._trigger_list`, which is the
        recommended method for overrides.

        :param Optional[Union[datetime.datetime, list[datetime.datetime]]] at:
            When to execute the cron, at one or several moments in time instead
            of as soon as possible.
        """
        if at is None:
            at_list = [fields.Datetime.now()]
        elif isinstance(at, datetime):
            at_list = [at]
        else:
            at_list = list(at)
            assert all(isinstance(at, datetime) for at in at_list)

        self._trigger_list(at_list)

    @api.model
    def _trigger_list(self, at_list):
        """
        Implementation of :meth:`~._trigger`.

        :param list[datetime.datetime] at_list:
            Execute the cron later, at precise moments in time.
        """
        if not at_list:
            return

        self.ensure_one()
        now = fields.Datetime.now()

        self.env['ir.cron.trigger'].sudo().create([
            {'cron_id': self.id, 'call_at': at}
            for at in at_list
        ])
        if _logger.isEnabledFor(logging.DEBUG):
            ats = ', '.join(map(str, at_list))
            _logger.debug("will execute '%s' at %s", self.sudo().name, ats)

        if min(at_list) <= now or os.getenv('ODOO_NOTIFY_CRON_CHANGES'):
            self._cr.postcommit.add(self._notifydb)

    def _notifydb(self):
        """ Wake up the cron workers
        The ODOO_NOTIFY_CRON_CHANGES environment variable allows to force the notifydb on both
        ir_cron modification and on trigger creation (regardless of call_at)
        """
        with odoo.sql_db.db_connect('postgres').cursor() as cr:
            cr.execute('NOTIFY cron_trigger, %s', [self.env.cr.dbname])
        _logger.debug("cron workers notified")


class ir_cron_trigger(models.Model):
    _name = 'ir.cron.trigger'
    _description = 'Triggered actions'

    cron_id = fields.Many2one("ir.cron", index=True)
    call_at = fields.Datetime()
