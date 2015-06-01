# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from pcalendar import Calendar, WorkingDate, StartDate, EndDate, Minutes

from task import Project, BalancedProject, AdjustedProject, Task, \
    STRICT, SLOPPY, SMART, Multi, YearlyMax, WeeklyMax, MonthlyMax, \
    DailyMax, VariableLoad

from resource import Resource
