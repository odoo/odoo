# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-TODAY OpenERP S.A. <http://www.openerp.com>
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################
import logging
import threading
import time
import psycopg2
from datetime import datetime
from dateutil.relativedelta import relativedelta

import openerp
from openerp import netsvc
from openerp.osv import fields, osv
from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT
from openerp.tools.safe_eval import safe_eval as eval
from openerp.tools.translate import _
from openerp.modules import load_information_from_description_file

_logger = logging.getLogger(__name__)

BASE_VERSION = load_information_from_description_file('base')['version']

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

class ir_cron(osv.osv):
    """ Model describing cron jobs (also called actions or tasks).
    """

    # TODO: perhaps in the future we could consider a flag on ir.cron jobs
    # that would cause database wake-up even if the database has not been
    # loaded yet or was already unloaded (e.g. 'force_db_wakeup' or something)
    # See also openerp.cron

    _name = "ir.cron"
    _order = 'name'
    _columns = {
        'name': fields.char('Name', required=True),
        'user_id': fields.many2one('res.users', 'User', required=True),
        'active': fields.boolean('Active'),
        'interval_number': fields.integer('Interval Number',help="Repeat every x."),
        'interval_type': fields.selection( [('minutes', 'Minutes'),
            ('hours', 'Hours'), ('work_days','Work Days'), ('days', 'Days'),('weeks', 'Weeks'), ('months', 'Months')], 'Interval Unit'),
        'numbercall': fields.integer('Number of Calls', help='How many times the method is called,\na negative number indicates no limit.'),
        'doall' : fields.boolean('Repeat Missed', help="Specify if missed occurrences should be executed when the server restarts."),
        'nextcall' : fields.datetime('Next Execution Date', required=True, help="Next planned execution date for this job."),
        'model': fields.char('Object', help="Model name on which the method to be called is located, e.g. 'res.partner'."),
        'function': fields.char('Method', help="Name of the method to be called when this job is processed."),
        'args': fields.text('Arguments', help="Arguments to be passed to the method, e.g. (uid,)."),
        'priority': fields.integer('Priority', help='The priority of the job, as an integer: 0 means higher priority, 10 means lower priority.')
    }

    _defaults = {
        'nextcall' : lambda *a: time.strftime(DEFAULT_SERVER_DATETIME_FORMAT),
        'priority' : 5,
        'user_id' : lambda obj,cr,uid,context: uid,
        'interval_number' : 1,
        'interval_type' : 'months',
        'numbercall' : 1,
        'active' : 1,
        'doall' : 1
    }

    def _check_args(self, cr, uid, ids, context=None):
        try:
            for this in self.browse(cr, uid, ids, context):
                str2tuple(this.args)
        except Exception:
            return False
        return True

    _constraints = [
        (_check_args, 'Invalid arguments', ['args']),
    ]

    def _handle_callback_exception(self, cr, uid, model_name, method_name, args, job_id, job_exception):
        """ Method called when an exception is raised by a job.

        Simply logs the exception and rollback the transaction.

        :param model_name: model name on which the job method is located.
        :param method_name: name of the method to call when this job is processed.
        :param args: arguments of the method (without the usual self, cr, uid).
        :param job_id: job id.
        :param job_exception: exception raised by the job.

        """
        cr.rollback()
        _logger.exception("Call of self.pool.get('%s').%s(cr, uid, *%r) failed in Job %s" % (model_name, method_name, args, job_id))

    def _callback(self, cr, uid, model_name, method_name, args, job_id):
        """ Run the method associated to a given job

        It takes care of logging and exception handling.

        :param model_name: model name on which the job method is located.
        :param method_name: name of the method to call when this job is processed.
        :param args: arguments of the method (without the usual self, cr, uid).
        :param job_id: job id.
        """
        try:
            args = str2tuple(args)
            openerp.modules.registry.RegistryManager.check_registry_signaling(cr.dbname)
            registry = openerp.registry(cr.dbname)
            if model_name in registry:
                model = registry[model_name]
                if hasattr(model, method_name):
                    log_depth = (None if _logger.isEnabledFor(logging.DEBUG) else 1)
                    netsvc.log(_logger, logging.DEBUG, 'cron.object.execute', (cr.dbname,uid,'*',model_name,method_name)+tuple(args), depth=log_depth)
                    if _logger.isEnabledFor(logging.DEBUG):
                        start_time = time.time()
                    getattr(model, method_name)(cr, uid, *args)
                    if _logger.isEnabledFor(logging.DEBUG):
                        end_time = time.time()
                        _logger.debug('%.3fs (%s, %s)' % (end_time - start_time, model_name, method_name))
                    openerp.modules.registry.RegistryManager.signal_caches_change(cr.dbname)
                else:
                    msg = "Method `%s.%s` does not exist." % (model_name, method_name)
                    _logger.warning(msg)
            else:
                msg = "Model `%s` does not exist." % model_name
                _logger.warning(msg)
        except Exception, e:
            self._handle_callback_exception(cr, uid, model_name, method_name, args, job_id, e)

    def _process_job(self, job_cr, job, cron_cr):
        """ Run a given job taking care of the repetition.

        :param job_cr: cursor to use to execute the job, safe to commit/rollback
        :param job: job to be run (as a dictionary).
        :param cron_cr: cursor holding lock on the cron job row, to use to update the next exec date,
            must not be committed/rolled back!
        """
        try:
            now = datetime.now() 
            nextcall = datetime.strptime(job['nextcall'], DEFAULT_SERVER_DATETIME_FORMAT)
            numbercall = job['numbercall']

            ok = False
            while nextcall < now and numbercall:
                if numbercall > 0:
                    numbercall -= 1
                if not ok or job['doall']:
                    self._callback(job_cr, job['user_id'], job['model'], job['function'], job['args'], job['id'])
                if numbercall:
                    nextcall += _intervalTypes[job['interval_type']](job['interval_number'])
                ok = True
            addsql = ''
            if not numbercall:
                addsql = ', active=False'
            cron_cr.execute("UPDATE ir_cron SET nextcall=%s, numbercall=%s"+addsql+" WHERE id=%s",
                       (nextcall.strftime(DEFAULT_SERVER_DATETIME_FORMAT), numbercall, job['id']))

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
        db = openerp.sql_db.db_connect(db_name)
        threading.current_thread().dbname = db_name
        cr = db.cursor()
        jobs = []
        try:
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
        finally:
            cr.close()

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
                    registry = openerp.registry(db_name)
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

        if hasattr(threading.current_thread(), 'dbname'): # cron job could have removed it as side-effect
            del threading.current_thread().dbname

    def _try_lock(self, cr, uid, ids, context=None):
        """Try to grab a dummy exclusive write-lock to the rows with the given ids,
           to make sure a following write() or unlink() will not block due
           to a process currently executing those cron tasks"""
        try:
            cr.execute("""SELECT id FROM "%s" WHERE id IN %%s FOR UPDATE NOWAIT""" % self._table,
                       (tuple(ids),), log_exceptions=False)
        except psycopg2.OperationalError:
            cr.rollback() # early rollback to allow translations to work for the user feedback
            raise osv.except_osv(_("Record cannot be modified right now"),
                                 _("This cron task is currently being executed and may not be modified, "
                                  "please try again in a few minutes"))

    def create(self, cr, uid, vals, context=None):
        res = super(ir_cron, self).create(cr, uid, vals, context=context)
        return res

    def write(self, cr, uid, ids, vals, context=None):
        self._try_lock(cr, uid, ids, context)
        res = super(ir_cron, self).write(cr, uid, ids, vals, context=context)
        return res

    def unlink(self, cr, uid, ids, context=None):
        self._try_lock(cr, uid, ids, context)
        res = super(ir_cron, self).unlink(cr, uid, ids, context=context)
        return res

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
