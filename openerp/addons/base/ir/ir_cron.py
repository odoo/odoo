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

import calendar
import time
import logging
import threading
import psycopg2
from datetime import datetime
from dateutil.relativedelta import relativedelta

import netsvc
import openerp
import pooler
import tools
from openerp.cron import WAKE_UP_NOW
from osv import fields, osv
from tools import DEFAULT_SERVER_DATETIME_FORMAT
from tools.safe_eval import safe_eval as eval
from tools.translate import _

_logger = logging.getLogger(__name__)

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
        'name': fields.char('Name', size=60, required=True),
        'user_id': fields.many2one('res.users', 'User', required=True),
        'active': fields.boolean('Active'),
        'interval_number': fields.integer('Interval Number',help="Repeat every x."),
        'interval_type': fields.selection( [('minutes', 'Minutes'),
            ('hours', 'Hours'), ('work_days','Work Days'), ('days', 'Days'),('weeks', 'Weeks'), ('months', 'Months')], 'Interval Unit'),
        'numbercall': fields.integer('Number of Calls', help='How many times the method is called,\na negative number indicates no limit.'),
        'doall' : fields.boolean('Repeat Missed', help="Specify if missed occurrences should be executed when the server restarts."),
        'nextcall' : fields.datetime('Next Execution Date', required=True, help="Next planned execution date for this job."),
        'model': fields.char('Object', size=64, help="Model name on which the method to be called is located, e.g. 'res.partner'."),
        'function': fields.char('Method', size=64, help="Name of the method to be called when this job is processed."),
        'args': fields.text('Arguments', help="Arguments to be passed to the method, e.g. (uid,)."),
        'priority': fields.integer('Priority', help='The priority of the job, as an integer: 0 means higher priority, 10 means lower priority.')
    }

    _defaults = {
        'nextcall' : lambda *a: time.strftime(DEFAULT_SERVER_DATETIME_FORMAT),
        'priority' : lambda *a: 5,
        'user_id' : lambda obj,cr,uid,context: uid,
        'interval_number' : lambda *a: 1,
        'interval_type' : lambda *a: 'months',
        'numbercall' : lambda *a: 1,
        'active' : lambda *a: 1,
        'doall' : lambda *a: 1
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
        args = str2tuple(args)
        model = self.pool.get(model_name)
        if model and hasattr(model, method_name):
            method = getattr(model, method_name)
            try:
                log_depth = (None if _logger.isEnabledFor(logging.DEBUG) else 1)
                netsvc.log(_logger, logging.DEBUG, 'cron.object.execute', (cr.dbname,uid,'*',model_name,method_name)+tuple(args), depth=log_depth)
                if _logger.isEnabledFor(logging.DEBUG):
                    start_time = time.time()
                method(cr, uid, *args)
                if _logger.isEnabledFor(logging.DEBUG):
                    end_time = time.time()
                    _logger.debug('%.3fs (%s, %s)' % (end_time - start_time, model_name, method_name))
            except Exception, e:
                self._handle_callback_exception(cr, uid, model_name, method_name, args, job_id, e)

    def _run_job(self, cr, job, now):
        """ Run a given job taking care of the repetition.

        The cursor has a lock on the job (aquired by _run_jobs_multithread()) and this
        method is run in a worker thread (spawned by _run_jobs_multithread())).

        :param job: job to be run (as a dictionary).
        :param now: timestamp (result of datetime.now(), no need to call it multiple time).

        """
        try:
            nextcall = datetime.strptime(job['nextcall'], DEFAULT_SERVER_DATETIME_FORMAT)
            numbercall = job['numbercall']

            ok = False
            while nextcall < now and numbercall:
                if numbercall > 0:
                    numbercall -= 1
                if not ok or job['doall']:
                    self._callback(cr, job['user_id'], job['model'], job['function'], job['args'], job['id'])
                if numbercall:
                    nextcall += _intervalTypes[job['interval_type']](job['interval_number'])
                ok = True
            addsql = ''
            if not numbercall:
                addsql = ', active=False'
            cr.execute("UPDATE ir_cron SET nextcall=%s, numbercall=%s"+addsql+" WHERE id=%s",
                       (nextcall.strftime(DEFAULT_SERVER_DATETIME_FORMAT), numbercall, job['id']))

            if numbercall:
                # Reschedule our own main cron thread if necessary.
                # This is really needed if this job runs longer than its rescheduling period.
                nextcall = calendar.timegm(nextcall.timetuple())
                openerp.cron.schedule_wakeup(nextcall, cr.dbname)
        finally:
            cr.commit()
            cr.close()
            openerp.cron.release_thread_slot()

    def _run_jobs_multithread(self):
        # TODO remove 'check' argument from addons/base_action_rule/base_action_rule.py
        """ Process the cron jobs by spawning worker threads.

        This selects in database all the jobs that should be processed. It then
        tries to lock each of them and, if it succeeds, spawns a thread to run
        the cron job (if it doesn't succeed, it means the job was already
        locked to be taken care of by another thread).

        The cursor used to lock the job in database is given to the worker
        thread (which has to close it itself).

        """
        db = self.pool.db
        cr = db.cursor()
        db_name = db.dbname
        try:
            jobs = {} # mapping job ids to jobs for all jobs being processed.
            now = datetime.now() 
            # Careful to compare timestamps with 'UTC' - everything is UTC as of v6.1.
            cr.execute("""SELECT * FROM ir_cron
                          WHERE numbercall != 0
                              AND active AND nextcall <= (now() at time zone 'UTC')
                          ORDER BY priority""")
            for job in cr.dictfetchall():
                if not openerp.cron.get_thread_slots():
                    break
                jobs[job['id']] = job

                task_cr = db.cursor()
                try:
                    # Try to grab an exclusive lock on the job row from within the task transaction
                    acquired_lock = False
                    task_cr.execute("""SELECT *
                                       FROM ir_cron
                                       WHERE id=%s
                                       FOR UPDATE NOWAIT""",
                                   (job['id'],), log_exceptions=False)
                    acquired_lock = True
                except psycopg2.OperationalError, e:
                    if e.pgcode == '55P03':
                        # Class 55: Object not in prerequisite state; 55P03: lock_not_available
                        _logger.debug('Another process/thread is already busy executing job `%s`, skipping it.', job['name'])
                        continue
                    else:
                        # Unexpected OperationalError
                        raise
                finally:
                    if not acquired_lock:
                        # we're exiting due to an exception while acquiring the lot
                        task_cr.close()

                # Got the lock on the job row, now spawn a thread to execute it in the transaction with the lock
                task_thread = threading.Thread(target=self._run_job, name=job['name'], args=(task_cr, job, now))
                # force non-daemon task threads (the runner thread must be daemon, and this property is inherited by default)
                task_thread.setDaemon(False)
                openerp.cron.take_thread_slot()
                task_thread.start()
                _logger.debug('Cron execution thread for job `%s` spawned', job['name'])

            # Find next earliest job ignoring currently processed jobs (by this and other cron threads)
            find_next_time_query = """SELECT min(nextcall) AS min_next_call
                                      FROM ir_cron WHERE numbercall != 0 AND active""" 
            if jobs:
                cr.execute(find_next_time_query + " AND id NOT IN %s", (tuple(jobs.keys()),))
            else:
                cr.execute(find_next_time_query)
            next_call = cr.dictfetchone()['min_next_call']

            if next_call:
                next_call = calendar.timegm(time.strptime(next_call, DEFAULT_SERVER_DATETIME_FORMAT))
            else:
                # no matching cron job found in database, re-schedule arbitrarily in 1 day,
                # this delay will likely be modified when running jobs complete their tasks
                next_call = time.time() + (24*3600)

            openerp.cron.schedule_wakeup(next_call, db_name)

        except Exception, ex:
            _logger.warning('Exception in cron:', exc_info=True)

        finally:
            cr.commit()
            cr.close()

    def update_running_cron(self, cr):
        """ Schedule as soon as possible a wake-up for this database. """
        # Verify whether the server is already started and thus whether we need to commit
        # immediately our changes and restart the cron agent in order to apply the change
        # immediately. The commit() is needed because as soon as the cron is (re)started it
        # will query the database with its own cursor, possibly before the end of the
        # current transaction.
        # This commit() is not an issue in most cases, but we must absolutely avoid it
        # when the server is only starting or loading modules (hence the test on pool._init).
        if not self.pool._init:
            cr.commit()
            openerp.cron.schedule_wakeup(WAKE_UP_NOW, self.pool.db.dbname)

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
        self.update_running_cron(cr)
        return res

    def write(self, cr, uid, ids, vals, context=None):
        self._try_lock(cr, uid, ids, context)
        res = super(ir_cron, self).write(cr, uid, ids, vals, context=context)
        self.update_running_cron(cr)
        return res

    def unlink(self, cr, uid, ids, context=None):
        self._try_lock(cr, uid, ids, context)
        res = super(ir_cron, self).unlink(cr, uid, ids, context=context)
        self.update_running_cron(cr)
        return res
ir_cron()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
