# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2011-TODAY OpenERP S.A. <http://www.openerp.com>
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

from datetime import datetime

import openerp

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

class test_ir_cron(openerp.osv.osv.osv):
    """ Add a few handy methods to test cron jobs scheduling. """
    _inherit = "ir.cron"

    def _0_seconds(a, b, c):
        print ">>> _0_seconds"

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

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

