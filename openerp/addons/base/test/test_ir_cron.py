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

import time
from datetime import datetime
from dateutil.relativedelta import relativedelta

import openerp

JOB = {
    'function': u'_0_seconds',
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

    # This test assumes 4 cron threads.
    def test_00(self, cr, uid):
        self.test_00_set = set()
        now = datetime.now()
        t1 = (now + relativedelta(minutes=1)).strftime('%Y-%m-%d %H:%M:%S')
        t2 = (now + relativedelta(minutes=1, seconds=5)).strftime('%Y-%m-%d %H:%M:%S')
        t3 = (now + relativedelta(minutes=1, seconds=10)).strftime('%Y-%m-%d %H:%M:%S')
        self.create(cr, uid, dict(JOB, name='test_00 _20_seconds_A', function='_20_seconds_A', nextcall=t1))
        self.create(cr, uid, dict(JOB, name='test_00 _20_seconds_B', function='_20_seconds_B', nextcall=t2))
        self.create(cr, uid, dict(JOB, name='test_00 _20_seconds_C', function='_20_seconds_C', nextcall=t3))

    def _expect(self, cr, uid, to_add, to_sleep, to_expect_in, to_expect_out):
        assert self.test_00_set == to_expect_in
        self.test_00_set.add(to_add)
        time.sleep(to_sleep)
        self.test_00_set.discard(to_add)
        assert self.test_00_set == to_expect_out

    def _20_seconds_A(self, cr, uid):
        self._expect(cr, uid, 'A', 20, set(), set(['B', 'C']))

    def _20_seconds_B(self, cr, uid):
        self._expect(cr, uid, 'B', 20, set('A'), set('C'))

    def _20_seconds_C(self, cr, uid):
        self._expect(cr, uid, 'C', 20, set(['A', 'B']), set())

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

