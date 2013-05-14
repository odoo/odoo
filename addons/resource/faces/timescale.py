############################################################################
#   Copyright (C) 2005 by Reithinger GmbH
#   mreithinger@web.de
#
#   This file is part of faces.
#                                                                         
#   faces is free software; you can redistribute it and/or modify
#   it under the terms of the GNU General Public License as published by
#   the Free Software Foundation; either version 2 of the License, or
#   (at your option) any later version.
#
#   faces is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU General Public License for more details.
#
#   You should have received a copy of the GNU General Public License
#   along with this program; if not, write to the
#   Free Software Foundation, Inc.,
#   51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
############################################################################

import faces.pcalendar as pcal
import matplotlib.cbook as cbook
import datetime
import sys


class TimeScale(object):
    def __init__(self, calendar):
        self.data_calendar = calendar
        self._create_chart_calendar()
        self.now = self.to_num(self.data_calendar.now)
                

    def to_datetime(self, xval):
        return xval.to_datetime()


    def to_num(self, date):
        return self.chart_calendar.WorkingDate(date)


    def is_free_slot(self, value):
        dt1 = self.chart_calendar.to_starttime(value)
        dt2 = self.data_calendar.to_starttime\
              (self.data_calendar.from_datetime(dt1))
        return dt1 != dt2


    def is_free_day(self, value):
        dt1 = self.chart_calendar.to_starttime(value)
        dt2 = self.data_calendar.to_starttime\
              (self.data_calendar.from_datetime(dt1))
        return dt1.date() != dt2.date()


    def _create_chart_calendar(self):
        dcal = self.data_calendar
        ccal = self.chart_calendar = pcal.Calendar()
        ccal.minimum_time_unit = 1

        #pad worktime slots of calendar (all days should be equally long)
        slot_sum = lambda slots: sum(map(lambda slot: slot[1] - slot[0], slots))
        day_sum = lambda day: slot_sum(dcal.get_working_times(day))
        
        max_work_time = max(map(day_sum, range(7)))

        #working_time should have 2/3
        sum_time = 3 * max_work_time / 2

        #now create timeslots for ccal
        def create_time_slots(day):
            src_slots = dcal.get_working_times(day)
            slots = [0, src_slots, 24*60]
            slots = tuple(cbook.flatten(slots))
            slots = zip(slots[:-1], slots[1:])

            #balance non working slots
            work_time = slot_sum(src_slots)
            non_work_time = sum_time - work_time

            non_slots = filter(lambda s: s not in src_slots, slots)
            non_slots = map(lambda s: (s[1] - s[0], s), non_slots)
            non_slots.sort()

            slots = []
            i = 0
            for l, s in non_slots:
                delta = non_work_time / (len(non_slots) - i)
                delta = min(l, delta)
                non_work_time -= delta
                slots.append((s[0], s[0] + delta))
                i += 1

            slots.extend(src_slots)
            slots.sort()
            return slots

        min_delta = sys.maxint
        for i in range(7):
            slots = create_time_slots(i)
            ccal.working_times[i] = slots
            min_delta = min(min_delta, min(map(lambda s: s[1] - s[0], slots)))

        ccal._recalc_working_time()

        self.slot_delta = min_delta
        self.day_delta = sum_time
        self.week_delta = ccal.week_time


_default_scale = TimeScale(pcal._default_calendar)

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
