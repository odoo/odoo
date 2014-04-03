# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Business Applications
#    Copyright (c) 2012-TODAY OpenERP S.A. <http://openerp.com>
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
from openerp.osv.orm import except_orm
from openerp.tests import common
import pytz
from pytz import timezone
from openerp import tools
import datetime


class TestEventTrackCases(common.TransactionCase):
    def setUp(self):
        super(TestEventTrackCases, self).setUp()
        
    def test_00_scheduling_algo(self):
        cr, uid = self.cr, self.uid
        event_track = self.registry('event.track')
        slot_list = []
        local_tz = pytz.timezone('UTC')
        def test_slots(datetime, duration, slot_list):
            st, et, key = event_track.convert_time(datetime, duration, local_tz)
            return event_track.calculate_slots(st, et, slot_list)
        
        #scenario 1
        for test in [('2014-06-04 04:00:00', 30), ('2014-06-04 03:55:00', 36)]:
            slot_list = test_slots(test[0], test[1], slot_list)
        
        self.assertEqual(len(slot_list),3)
        self.assertEqual(slot_list[0][0].strftime(tools.DEFAULT_SERVER_DATETIME_FORMAT),'2014-06-04 03:55:00')
        self.assertEqual(slot_list[len(slot_list) - 1][1].strftime(tools.DEFAULT_SERVER_DATETIME_FORMAT),'2014-06-04 04:31:00')
        slot_list = []
        
        #scenario 2
        for test in [('2014-06-04 04:00:00', 30), ('2014-06-04 04:35:00', 30)]:
            slot_list = test_slots(test[0], test[1], slot_list)
            
        self.assertEqual(len(slot_list),3)
        self.assertEqual(slot_list[0][0].strftime(tools.DEFAULT_SERVER_DATETIME_FORMAT),'2014-06-04 04:00:00')
        self.assertEqual(slot_list[len(slot_list) - 1][1].strftime(tools.DEFAULT_SERVER_DATETIME_FORMAT),'2014-06-04 05:05:00')
        slot_list = []
        
        #scenario 3
        for test in [('2014-06-04 04:00:00', 30), ('2014-06-04 03:00:00', 30)]:
            slot_list = test_slots(test[0], test[1], slot_list)
        
        self.assertEqual(len(slot_list), 3)
        self.assertEqual(slot_list[0][0].strftime(tools.DEFAULT_SERVER_DATETIME_FORMAT),'2014-06-04 03:00:00')
        self.assertEqual(slot_list[len(slot_list) - 1][1].strftime(tools.DEFAULT_SERVER_DATETIME_FORMAT),'2014-06-04 04:30:00')
        slot_list = []

        #scenario 4
        for test in [('2014-06-04 04:00:00', 30), ('2014-06-04 04:05:00', 10)]:
            slot_list = test_slots(test[0], test[1], slot_list)
        
        self.assertEqual(len(slot_list), 3)
        self.assertEqual(slot_list[0][0].strftime(tools.DEFAULT_SERVER_DATETIME_FORMAT),'2014-06-04 04:00:00')
        self.assertEqual(slot_list[len(slot_list) - 1][1].strftime(tools.DEFAULT_SERVER_DATETIME_FORMAT),'2014-06-04 04:30:00')
        slot_list = []
        
        #scenario 5
        for test in [('2014-06-04 04:00:00', 30), ('2014-06-04 03:35:00', 30)]:
            slot_list = test_slots(test[0], test[1], slot_list)
        
        self.assertEqual(len(slot_list), 3)
        self.assertEqual(slot_list[0][0].strftime(tools.DEFAULT_SERVER_DATETIME_FORMAT),'2014-06-04 03:35:00')
        self.assertEqual(slot_list[len(slot_list) - 1][1].strftime(tools.DEFAULT_SERVER_DATETIME_FORMAT),'2014-06-04 04:30:00')
        slot_list = []
        
        #scenario 6
        for test in [('2014-06-04 04:00:00', 30), ('2014-06-04 04:15:00', 30)]:
            slot_list = test_slots(test[0], test[1], slot_list)
        
        self.assertEqual(len(slot_list), 3)
        self.assertEqual(slot_list[0][0].strftime(tools.DEFAULT_SERVER_DATETIME_FORMAT),'2014-06-04 04:00:00')
        self.assertEqual(slot_list[len(slot_list) - 1][1].strftime(tools.DEFAULT_SERVER_DATETIME_FORMAT),'2014-06-04 04:45:00')
