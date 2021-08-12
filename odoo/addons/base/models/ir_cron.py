# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import logging
import threading
import time
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
    priority = fields.Integer(default=5, help='The priority of the job, as an integer: 0 means higher priority, 10 means lower priority.')

    @api.model
    def create(self, values):
        values['usage'] = 'ir_cron'
        return super(ir_cron, self).create(values)

    @api.model
    def default_get(self, fields_list):
        # only 'code' state is supported for cron job so set it as default
        if not self._context.get('default_state'):
            self = self.with_context(default_state='code')
        return super(ir_cron, self).default_get(fields_list)

    @api.multi
    def method_direct_trigger(self):
        self.check_access_rights('write')
        for cron in self:
            self.sudo(user=cron.user_id.id).ir_actions_server_id.run()
        return True

    @api.model
    def _handle_callback_exception(self, cron_name, server_action_id, job_id, job_exception):
        """ Method called when an exception is raised by a job.

        Simply logs the exception and rollback the transaction. """
        self._cr.rollback()

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
            if _logger.isEnabledFor(logging.DEBUG):
                start_time = time.time()
            self.env['ir.actions.server'].browse(server_action_id).run()
            if start_time and _logger.isEnabledFor(logging.DEBUG):
                end_time = time.time()
                _logger.debug('%.3fs (cron %s, server action %d with uid %d)', end_time - start_time, cron_name, server_action_id, self.env.uid)
            self.pool.signal_changes()
        except Exception as e:
            self.pool.reset_changes()
            _logger.exception("Call from cron %s for server action #%s failed in Job #%s",
                              cron_name, server_action_id, job_id)
            self._handle_callback_exception(cron_name, server_action_id, job_id, e)

    @classmethod
    def _process_job(cls, job_cr, job, cron_cr):
        """ Run a given job taking care of the repetition.

        :param job_cr: cursor to use to execute the job, safe to commit/rollback
        :param job: job to be run (as a dictionary).
        :param cron_cr: cursor holding lock on the cron job row, to use to update the next exec date,
            must not be committed/rolled back!
        """
        try:
            with api.Environment.manage():
                cron = api.Environment(job_cr, job['user_id'], {})[cls._name]
                # Use the user's timezone to compare and compute datetimes,
                # otherwise unexpected results may appear. For instance, adding
                # 1 month in UTC to July 1st at midnight in GMT+2 gives July 30
                # instead of August 1st!
                now = fields.Datetime.context_timestamp(cron, datetime.now())
                nextcall = fields.Datetime.context_timestamp(cron, fields.Datetime.from_string(job['nextcall']))
                numbercall = job['numbercall']

                ok = False
                while nextcall < now and numbercall:
                    if numbercall > 0:
                        numbercall -= 1
                    if not ok or job['doall']:
                        cron._callback(job['cron_name'], job['ir_actions_server_id'], job['id'])
                    if numbercall:
                        nextcall += _intervalTypes[job['interval_type']](job['interval_number'])
                    ok = True
                addsql = ''
                if not numbercall:
                    addsql = ', active=False'
                cron_cr.execute("UPDATE ir_cron SET nextcall=%s, numbercall=%s"+addsql+" WHERE id=%s",
                                (fields.Datetime.to_string(nextcall.astimezone(pytz.UTC)), numbercall, job['id']))
                cron.invalidate_cache()

        finally:
            job_cr.commit()
            cron_cr.commit()

    @classmethod
    def _process_jobs(cls, db_name):
        """ Try to process all cron jobs.

        This selects in database all the jobs that should be processed. It then
        tries to lock each of them and, if it succeeds, run the cron job (if it
        doesn't succeed, it means the job was already locked to be taken care
        of by another thread) and return.

        :raise BadVersion: if the version is different from the worker's
        :raise BadModuleState: if modules are to install/upgrade/remove
        """
        db = odoo.sql_db.db_connect(db_name)
        threading.current_thread().dbname = db_name
        try:
            with db.cursor() as cr:
                # Make sure the database has the same version as the code of
                # base and that no module must be installed/upgraded/removed
                cr.execute("SELECT latest_version FROM ir_module_module WHERE name=%s", ['base'])
                (version,) = cr.fetchone()
                cr.execute("SELECT COUNT(*) FROM ir_module_module WHERE state LIKE %s", ['to %'])
                (changes,) = cr.fetchone()
                if version is None:
                    raise BadModuleState()
                elif version != BASE_VERSION:
                    raise BadVersion()
                # Careful to compare timestamps with 'UTC' - everything is UTC as of v6.1.
                cr.execute("""SELECT * FROM ir_cron
                              WHERE numbercall != 0
                                  AND active AND nextcall <= (now() at time zone 'UTC')
                              ORDER BY priority""")
                jobs = cr.dictfetchall()

            if changes:
                if not jobs:
                    raise BadModuleState()
                # nextcall is never updated if the cron is not executed,
                # it is used as a sentinel value to check whether cron jobs
                # have been locked for a long time (stuck)
                parse = fields.Datetime.from_string
                oldest = min([parse(job['nextcall']) for job in jobs])
                if datetime.now() - oldest > MAX_FAIL_TIME:
                    odoo.modules.reset_modules_state(db_name)
                else:
                    raise BadModuleState()

            for job in jobs:
                lock_cr = db.cursor()
                try:
                    # Try to grab an exclusive lock on the job row from within the task transaction
                    # Restrict to the same conditions as for the search since the job may have already
                    # been run by an other thread when cron is running in multi thread
                    lock_cr.execute("""SELECT *
                                       FROM ir_cron
                                       WHERE numbercall != 0
                                          AND active
                                          AND nextcall <= (now() at time zone 'UTC')
                                          AND id=%s
                                       FOR UPDATE NOWAIT""",
                                   (job['id'],), log_exceptions=False)

                    locked_job = lock_cr.fetchone()
                    if not locked_job:
                        _logger.debug("Job `%s` already executed by another process/thread. skipping it", job['cron_name'])
                        continue
                    # Got the lock on the job row, run its code
                    _logger.info('Starting job `%s`.', job['cron_name'])
                    job_cr = db.cursor()
                    try:
                        registry = odoo.registry(db_name)
                        registry[cls._name]._process_job(job_cr, job, lock_cr)
                        _logger.info('Job `%s` done.', job['cron_name'])
                    except Exception:
                        _logger.exception('Unexpected exception while processing cron job %r', job)
                    finally:
                        job_cr.close()

                except psycopg2.OperationalError as e:
                    if e.pgcode == '55P03':
                        # Class 55: Object not in prerequisite state; 55P03: lock_not_available
                        _logger.debug('Another process/thread is already busy executing job `%s`, skipping it.', job['cron_name'])
                        continue
                    else:
                        # Unexpected OperationalError
                        raise
                finally:
                    # we're exiting due to an exception while acquiring the lock
                    lock_cr.close()

        finally:
            if hasattr(threading.current_thread(), 'dbname'):
                del threading.current_thread().dbname

    @classmethod
    def _acquire_job(cls, db_name):
        """ Try to process all cron jobs.

        This selects in database all the jobs that should be processed. It then
        tries to lock each of them and, if it succeeds, run the cron job (if it
        doesn't succeed, it means the job was already locked to be taken care
        of by another thread) and return.

        This method hides most exceptions related to the database's version, the
        modules' state, and such.
        """
        try:
            cls._process_jobs(db_name)
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

    @api.multi
    def _try_lock(self):
        """Try to grab a dummy exclusive write-lock to the rows with the given ids,
           to make sure a following write() or unlink() will not block due
           to a process currently executing those cron tasks"""
        try:
            self._cr.execute("""SELECT id FROM "%s" WHERE id IN %%s FOR UPDATE NOWAIT""" % self._table,
                             [tuple(self.ids)], log_exceptions=False)
        except psycopg2.OperationalError:
            self._cr.rollback()  # early rollback to allow translations to work for the user feedback
            raise UserError(_("Record cannot be modified right now: "
                              "This cron task is currently being executed and may not be modified "
                              "Please try again in a few minutes"))

    @api.multi
    def write(self, vals):
        self._try_lock()
        return super(ir_cron, self).write(vals)

    @api.multi
    def unlink(self):
        self._try_lock()
        return super(ir_cron, self).unlink()

    @api.multi
    def try_write(self, values):
        try:
            with self._cr.savepoint():
                self._cr.execute("""SELECT id FROM "%s" WHERE id IN %%s FOR UPDATE NOWAIT""" % self._table,
                                 [tuple(self.ids)], log_exceptions=False)
        except psycopg2.OperationalError:
            pass
        else:
            return super(ir_cron, self).write(values)
        return False

    @api.model
    def toggle(self, model, domain):
        active = bool(self.env[model].search_count(domain))
        return self.try_write({'active': active})
