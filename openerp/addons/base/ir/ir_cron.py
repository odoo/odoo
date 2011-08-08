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

import time
import logging
import threading
import psycopg2
from datetime import datetime
from dateutil.relativedelta import relativedelta
import netsvc
import tools
from tools.safe_eval import safe_eval as eval
import pooler
from osv import fields, osv
import openerp

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

JOB = {
    'function': u'f',
    'interval_type': u'minutes',
    'user_id': 1,
    'name': u'test',
    'args': False,
    'numbercall': 1,
    'nextcall': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
    'priority': 5,
    'doall': True,
    'active': True,
    'interval_number': 1,
    'model': u'ir.cron'
}

class ir_cron(osv.osv):
    """ This is the ORM object that periodically executes actions.
    """
    _name = "ir.cron"
    _order = 'name'
    _columns = {
        'name': fields.char('Name', size=60, required=True),
        'user_id': fields.many2one('res.users', 'User', required=True),
        'active': fields.boolean('Active'),
        'interval_number': fields.integer('Interval Number',help="Repeat every x."),
        'interval_type': fields.selection( [('minutes', 'Minutes'),
            ('hours', 'Hours'), ('work_days','Work Days'), ('days', 'Days'),('weeks', 'Weeks'), ('months', 'Months')], 'Interval Unit'),
        'numbercall': fields.integer('Number of Calls', help='Number of time the function is called,\na negative number indicates no limit'),
        'doall' : fields.boolean('Repeat Missed', help="Enable this if you want to execute missed occurences as soon as the server restarts."),
        'nextcall' : fields.datetime('Next Execution Date', required=True, help="Next planned execution date for this scheduler"),
        'model': fields.char('Object', size=64, help="Name of object whose function will be called when this scheduler will run. e.g. 'res.partener'"),
        'function': fields.char('Function', size=64, help="Name of the method to be called on the object when this scheduler is executed."),
        'args': fields.text('Arguments', help="Arguments to be passed to the method. e.g. (uid,)"),
        'priority': fields.integer('Priority', help='0=Very Urgent\n10=Not urgent')
    }

    _defaults = {
        'nextcall' : lambda *a: time.strftime('%Y-%m-%d %H:%M:%S'),
        'priority' : lambda *a: 5,
        'user_id' : lambda obj,cr,uid,context: uid,
        'interval_number' : lambda *a: 1,
        'interval_type' : lambda *a: 'months',
        'numbercall' : lambda *a: 1,
        'active' : lambda *a: 1,
        'doall' : lambda *a: 1
    }

    _logger = logging.getLogger('cron')

    def f(a, b, c):
        print ">>> in f"

    def expensive(a, b, c):
        print ">>> in expensive"
        time.sleep(80)
        print ">>> out expensive"

    def expensive_2(a, b, c):
        print ">>> in expensive_2"
        time.sleep(30)
        print ">>> out expensive_2"

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

    def _handle_callback_exception(self, cr, uid, model, func, args, job_id, job_exception):
        cr.rollback()
        self._logger.exception("Call of self.pool.get('%s').%s(cr, uid, *%r) failed in Job %s" % (model, func, args, job_id))

    def _callback(self, cr, uid, model, func, args, job_id):
        args = str2tuple(args)
        m = self.pool.get(model)
        if m and hasattr(m, func):
            f = getattr(m, func)
            try:
                netsvc.log('cron', (cr.dbname,uid,'*',model,func)+tuple(args), channel=logging.DEBUG,
                            depth=(None if self._logger.isEnabledFor(logging.DEBUG_RPC_ANSWER) else 1), fn='object.execute')
                logger = logging.getLogger('execution time')
                if logger.isEnabledFor(logging.DEBUG):
                    start_time = time.time()
                f(cr, uid, *args)
                if logger.isEnabledFor(logging.DEBUG):
                    end_time = time.time()
                    logger.log(logging.DEBUG, '%.3fs (%s, %s)' % (end_time - start_time, model, func))
            except Exception, e:
                self._handle_callback_exception(cr, uid, model, func, args, job_id, e)

    def _run_job(self, cr, job, now):
        """ Run a given job taking care of the repetition. """
        try:
            nextcall = datetime.strptime(job['nextcall'], '%Y-%m-%d %H:%M:%S')
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
            cr.execute("update ir_cron set nextcall=%s, numbercall=%s"+addsql+" where id=%s", (nextcall.strftime('%Y-%m-%d %H:%M:%S'), numbercall, job['id']))

            if numbercall:
                # Reschedule our own main cron thread if necessary.
                # This is really needed if this job runs longer than its rescheduling period.
                print ">>> advance at", nextcall
                nextcall = time.mktime(nextcall.timetuple())
                openerp.cron.schedule_in_advance(nextcall, cr.dbname)
        finally:
            cr.commit()
            cr.close()
            openerp.cron.inc_thread_count()

    def _run_jobs(self):
        # TODO remove 'check' argument from addons/base_action_rule/base_action_rule.py
        """ Process the cron jobs by spawning worker threads.

        This selects in database all the jobs that should be processed. It then
        try to lock each of them and, if it succeeds, spawn a thread to run the
        cron job (if doesn't succeed, it means another the job was already
        locked to be taken care of by another thread.

        """
        print ">>> _run_jobs"
        db = self.pool.db
        cr = db.cursor()
        db_name = db.dbname
        try:
            jobs = {} # mapping job ids to jobs for all jobs being processed.
            now = datetime.now()
            cr.execute('select * from ir_cron where numbercall<>0 and active and nextcall<=now() order by priority')
            for job in cr.dictfetchall():
                print ">>>", openerp.cron.get_thread_count(), "threads"
                if not openerp.cron.get_thread_count():
                    break
                task_cr = db.cursor()
                task_job = None
                jobs[job['id']] = job

                try:
                    # Try to lock the job...
                    task_cr.execute('select * from ir_cron where id=%s for update nowait', (job['id'],), log_exceptions=False)
                    task_job = task_cr.dictfetchall()[0]
                except psycopg2.OperationalError, e:
                    if e.pgcode == '55P03':
                        # Class 55: Object not in prerequisite state, 55P03: lock_not_available
                        # ... and fail.
                        print ">>>", job['name'], " is already being processed"
                        continue
                    else:
                        raise
                finally:
                    if not task_job:
                        task_cr.close()

                # ... and succeed.
                print ">>> taking care of", job['name']
                task_thread = threading.Thread(target=self._run_job, name=task_job['name'], args=(task_cr, task_job, now))
                # force non-daemon task threads (the runner thread must be daemon, and this property is inherited by default)
                task_thread.setDaemon(False)
                openerp.cron.dec_thread_count()
                task_thread.start()

            # Wake up time, without considering the currently processed jobs.
            if jobs.keys():
                cr.execute('select min(nextcall) as min_next_call from ir_cron where numbercall<>0 and active and id not in %s', (tuple(jobs.keys()),))
            else:
                cr.execute('select min(nextcall) as min_next_call from ir_cron where numbercall<>0 and active')
            next_call = cr.dictfetchone()['min_next_call']
            print ">>> possibility at ", next_call

            if next_call:
                next_call = time.mktime(time.strptime(next_call, '%Y-%m-%d %H:%M:%S'))
            else:
                next_call = int(time.time()) + 3600   # if do not find active cron job from database, it will run again after 1 day

            openerp.cron.schedule_in_advance(next_call, db_name)

        except Exception, ex:
            self._logger.warning('Exception in cron:', exc_info=True)

        finally:
            cr.commit()
            cr.close()

    def update_running_cron(self, cr):
        # Verify whether the server is already started and thus whether we need to commit
        # immediately our changes and restart the cron agent in order to apply the change
        # immediately. The commit() is needed because as soon as the cron is (re)started it
        # will query the database with its own cursor, possibly before the end of the
        # current transaction.
        # This commit() is not an issue in most cases, but we must absolutely avoid it
        # when the server is only starting or loading modules (hence the test on pool._init).
        if not self.pool._init:
            cr.commit()
            openerp.cron.schedule_in_advance(1, self.pool.db.dbname)

    def _20_seconds(self, cr, uid):
        print ">>> in _20_seconds"
        time.sleep(20)
        print ">>> out _20_seconds"

    def _80_seconds(self, cr, uid):
        print ">>> in _80_seconds"
        time.sleep(80)
        print ">>> out _80_seconds"

    def test_0(self, cr, uid):
        now = datetime.now()
        t1 = (now + relativedelta(minutes=1)).strftime('%Y-%m-%d %H:%M:%S')
        t2 = (now + relativedelta(minutes=1, seconds=5)).strftime('%Y-%m-%d %H:%M:%S')
        t3 = (now + relativedelta(minutes=1, seconds=10)).strftime('%Y-%m-%d %H:%M:%S')
        self.create(cr, uid, dict(JOB, name='test_0 _20_seconds A', function='_20_seconds', nextcall=t1))
        self.create(cr, uid, dict(JOB, name='test_0 _20_seconds B', function='_20_seconds', nextcall=t2))
        self.create(cr, uid, dict(JOB, name='test_0 _20_seconds C', function='_20_seconds', nextcall=t3))

    def test_1(self, cr, uid):
        now = datetime.now()
        t1 = (now + relativedelta(minutes=1)).strftime('%Y-%m-%d %H:%M:%S')
        self.create(cr, uid, dict(JOB, name='test_1 _20_seconds * 3', function='_20_seconds', nextcall=t1, numbercall=3))

    def test_2(self, cr, uid):
        now = datetime.now()
        t1 = (now + relativedelta(minutes=1)).strftime('%Y-%m-%d %H:%M:%S')
        self.create(cr, uid, dict(JOB, name='test_2 _80_seconds * 2', function='_80_seconds', nextcall=t1, numbercall=2))

    def test_3(self, cr, uid):
        now = datetime.now()
        t1 = (now + relativedelta(minutes=1)).strftime('%Y-%m-%d %H:%M:%S')
        t2 = (now + relativedelta(minutes=1, seconds=5)).strftime('%Y-%m-%d %H:%M:%S')
        t3 = (now + relativedelta(minutes=1, seconds=10)).strftime('%Y-%m-%d %H:%M:%S')
        self.create(cr, uid, dict(JOB, name='test_3 _80_seconds A', function='_80_seconds', nextcall=t1))
        self.create(cr, uid, dict(JOB, name='test_3 _20_seconds B', function='_20_seconds', nextcall=t2))
        self.create(cr, uid, dict(JOB, name='test_3 _20_seconds C', function='_20_seconds', nextcall=t3))

    def create(self, cr, uid, vals, context=None):
        res = super(ir_cron, self).create(cr, uid, vals, context=context)
        self.update_running_cron(cr)
        return res

    def write(self, cr, user, ids, vals, context=None):
        res = super(ir_cron, self).write(cr, user, ids, vals, context=context)
        self.update_running_cron(cr)
        return res

    def unlink(self, cr, uid, ids, context=None):
        res = super(ir_cron, self).unlink(cr, uid, ids, context=context)
        self.update_running_cron(cr)
        return res
ir_cron()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

