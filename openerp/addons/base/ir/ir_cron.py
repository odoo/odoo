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
from datetime import datetime
from dateutil.relativedelta import relativedelta
import netsvc
import tools
from tools.safe_eval import safe_eval as eval
import pooler
from osv import fields, osv

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

class ir_cron(osv.osv, netsvc.Agent):
    """ This is the ORM object that periodically executes actions.
        Note that we use the netsvc.Agent()._logger member.
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

    def _callback(self, cr, uid, model, func, args):
        args = str2tuple(args)
        m = self.pool.get(model)
        if m and hasattr(m, func):
            f = getattr(m, func)
            try:
                f(cr, uid, *args)
            except Exception, e:
                cr.rollback()
                self._logger.exception("Job call of self.pool.get('%s').%s(cr, uid, *%r) failed" % (model, func, args))


    def _poolJobs(self, db_name, check=False):
        try:
            db, pool = pooler.get_db_and_pool(db_name)
        except:
            return False
        cr = db.cursor()
        try:
            if not pool._init:
                now = datetime.now()
                cr.execute('select * from ir_cron where numbercall<>0 and active and nextcall<=now() order by priority')
                for job in cr.dictfetchall():
                    nextcall = datetime.strptime(job['nextcall'], '%Y-%m-%d %H:%M:%S')
                    numbercall = job['numbercall']

                    ok = False
                    while nextcall < now and numbercall:
                        if numbercall > 0:
                            numbercall -= 1
                        if not ok or job['doall']:
                            self._callback(cr, job['user_id'], job['model'], job['function'], job['args'])
                        if numbercall:
                            nextcall += _intervalTypes[job['interval_type']](job['interval_number'])
                        ok = True
                    addsql = ''
                    if not numbercall:
                        addsql = ', active=False'
                    cr.execute("update ir_cron set nextcall=%s, numbercall=%s"+addsql+" where id=%s", (nextcall.strftime('%Y-%m-%d %H:%M:%S'), numbercall, job['id']))
                    cr.commit()


            cr.execute('select min(nextcall) as min_next_call from ir_cron where numbercall<>0 and active')
            next_call = cr.dictfetchone()['min_next_call']
            if next_call:
                next_call = time.mktime(time.strptime(next_call, '%Y-%m-%d %H:%M:%S'))
            else:
                next_call = int(time.time()) + 3600   # if do not find active cron job from database, it will run again after 1 day

            if not check:
                self.setAlarm(self._poolJobs, next_call, db_name, db_name)

        except Exception, ex:
            self._logger.warning('Exception in cron:', exc_info=True)

        finally:
            cr.commit()
            cr.close()

    def restart(self, dbname):
        self.cancel(dbname)
        # Reschedule cron processing job asap, but not in the current thread
        self.setAlarm(self._poolJobs, time.time(), dbname, dbname)

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
            self.restart(cr.dbname)

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

