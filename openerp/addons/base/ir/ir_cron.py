# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import logging
import threading
import time
import psycopg2
import pytz
from datetime import datetime
from dateutil.relativedelta import relativedelta

import odoo
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
from odoo.tools.safe_eval import safe_eval as eval

_logger = logging.getLogger(__name__)

BASE_VERSION = odoo.modules.load_information_from_description_file('base')['version']


def str2tuple(s):
    return eval('tuple(%s)' % (s or ''))

_intervalTypes = {
    'work_days': lambda interval: relativedelta(days=interval),
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
    _order = 'name'

    name = fields.Char(required=True)
    user_id = fields.Many2one('res.users', string='User', default=lambda self: self.env.user, required=True)
    active = fields.Boolean(default=True)
    interval_number = fields.Integer(default=1, help="Repeat every x.")
    interval_type = fields.Selection([('minutes', 'Minutes'),
                                      ('hours', 'Hours'),
                                      ('work_days', 'Work Days'),
                                      ('days', 'Days'),
                                      ('weeks', 'Weeks'),
                                      ('months', 'Months')], string='Interval Unit', default='months')
    numbercall = fields.Integer(string='Number of Calls', default=1, help='How many times the method is called,\na negative number indicates no limit.')
    doall = fields.Boolean(string='Repeat Missed', help="Specify if missed occurrences should be executed when the server restarts.")
    nextcall = fields.Datetime(string='Next Execution Date', required=True, default=fields.Datetime.now, help="Next planned execution date for this job.")
    model = fields.Char(string='Object', help="Model name on which the method to be called is located, e.g. 'res.partner'.")
    function = fields.Char(string='Method', help="Name of the method to be called when this job is processed.")
    args = fields.Text(string='Arguments', help="Arguments to be passed to the method, e.g. (uid,).")
    priority = fields.Integer(default=5, help='The priority of the job, as an integer: 0 means higher priority, 10 means lower priority.')

    @api.constrains('args')
    def _check_args(self):
        try:
            for this in self:
                str2tuple(this.args)
        except Exception:
            raise ValidationError(_('Invalid arguments'))

    @api.multi
    def method_direct_trigger(self):
        for cron in self:
            self.sudo(user=cron.user_id.id)._callback(cron.model, cron.function, cron.args, cron.id)
        return True

    @api.model
    def _handle_callback_exception(self, model_name, method_name, args, job_id, job_exception):
        """ Method called when an exception is raised by a job.

        Simply logs the exception and rollback the transaction.

        :param model_name: model name on which the job method is located.
        :param method_name: name of the method to call when this job is processed.
        :param args: arguments of the method (without the usual self, cr, uid).
        :param job_id: job id.
        :param job_exception: exception raised by the job.

        """
        self._cr.rollback()
        _logger.exception("Call of self.env[%r].%s(*%r) failed in Job %s",
                          model_name, method_name, args, job_id)

    @api.model
    def _callback(self, model_name, method_name, args, job_id):
        """ Run the method associated to a given job

        It takes care of logging and exception handling.

        :param model_name: model name on which the job method is located.
        :param method_name: name of the method to call when this job is processed.
        :param args: arguments of the method (without the usual self, cr, uid).
        :param job_id: job id.
        """
        try:
            args = str2tuple(args)
            odoo.modules.registry.RegistryManager.check_registry_signaling(self._cr.dbname)
            if model_name in self.env:
                model = self.env[model_name]
                if hasattr(model, method_name):
                    log_depth = (None if _logger.isEnabledFor(logging.DEBUG) else 1)
                    odoo.netsvc.log(_logger, logging.DEBUG, 'cron.object.execute', (self._cr.dbname, self._uid, '*', model_name, method_name)+tuple(args), depth=log_depth)
                    if _logger.isEnabledFor(logging.DEBUG):
                        start_time = time.time()
                    getattr(model, method_name)(*args)
                    if _logger.isEnabledFor(logging.DEBUG):
                        end_time = time.time()
                        _logger.debug('%.3fs (%s, %s)', end_time - start_time, model_name, method_name)
                    odoo.modules.registry.RegistryManager.signal_caches_change(self._cr.dbname)
                else:
                    _logger.warning("Method '%s.%s' does not exist.", model_name, method_name)
            else:
                _logger.warning("Model %r does not exist.", model_name)
        except Exception, e:
            self._handle_callback_exception(model_name, method_name, args, job_id, e)

    def _process_job(self, job_cr, job, cron_cr):
        """ Run a given job taking care of the repetition.

        :param job_cr: cursor to use to execute the job, safe to commit/rollback
        :param job: job to be run (as a dictionary).
        :param cron_cr: cursor holding lock on the cron job row, to use to update the next exec date,
            must not be committed/rolled back!
        """
        try:
            with api.Environment.manage():
                cron = api.Environment(job_cr, job['user_id'], {})[self._name]
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
                        cron._callback(job['model'], job['function'], job['args'], job['id'])
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
    def _acquire_job(cls, db_name):
        # TODO remove 'check' argument from addons/base_action_rule/base_action_rule.py
        """ Try to process one cron job.

        This selects in database all the jobs that should be processed. It then
        tries to lock each of them and, if it succeeds, run the cron job (if it
        doesn't succeed, it means the job was already locked to be taken care
        of by another thread) and return.

        If a job was processed, returns True, otherwise returns False.
        """
        db = odoo.sql_db.db_connect(db_name)
        threading.current_thread().dbname = db_name
        jobs = []
        try:
            with db.cursor() as cr:
                # Make sure the database we poll has the same version as the code of base
                cr.execute("SELECT 1 FROM ir_module_module WHERE name=%s AND latest_version=%s", ('base', BASE_VERSION))
                if cr.fetchone():
                    # Careful to compare timestamps with 'UTC' - everything is UTC as of v6.1.
                    cr.execute("""SELECT * FROM ir_cron
                                  WHERE numbercall != 0
                                      AND active AND nextcall <= (now() at time zone 'UTC')
                                  ORDER BY priority""")
                    jobs = cr.dictfetchall()
                else:
                    _logger.warning('Skipping database %s as its base version is not %s.', db_name, BASE_VERSION)
        except psycopg2.ProgrammingError, e:
            if e.pgcode == '42P01':
                # Class 42 — Syntax Error or Access Rule Violation; 42P01: undefined_table
                # The table ir_cron does not exist; this is probably not an OpenERP database.
                _logger.warning('Tried to poll an undefined table on database %s.', db_name)
            else:
                raise
        except Exception:
            _logger.warning('Exception in cron:', exc_info=True)

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
                    _logger.debug("Job `%s` already executed by another process/thread. skipping it", job['name'])
                    continue
                # Got the lock on the job row, run its code
                _logger.debug('Starting job `%s`.', job['name'])
                job_cr = db.cursor()
                try:
                    registry = odoo.registry(db_name)
                    registry[cls._name]._process_job(job_cr, job, lock_cr)
                except Exception:
                    _logger.exception('Unexpected exception while processing cron job %r', job)
                finally:
                    job_cr.close()

            except psycopg2.OperationalError, e:
                if e.pgcode == '55P03':
                    # Class 55: Object not in prerequisite state; 55P03: lock_not_available
                    _logger.debug('Another process/thread is already busy executing job `%s`, skipping it.', job['name'])
                    continue
                else:
                    # Unexpected OperationalError
                    raise
            finally:
                # we're exiting due to an exception while acquiring the lock
                lock_cr.close()

        if hasattr(threading.current_thread(), 'dbname'):  # cron job could have removed it as side-effect
            del threading.current_thread().dbname

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
