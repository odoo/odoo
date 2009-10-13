# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution	
#    Copyright (C) 2004-2009 Tiny SPRL (<http://tiny.be>). All Rights Reserved
#    $Id$
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from sets import Set
from mx.DateTime import *

import StringIO

from report.render import render
from report.interface import report_int

from gantt import GanttCanvas
from _date_compute import _project_compute, _compute_tasks
import pooler

class external_pdf(render):
    def __init__(self, pdf):
        render.__init__(self)
        self.pdf = pdf
        self.output_type='pdf'
    
    def _render(self):
        return self.pdf

class report_tasks(report_int):
    def create(self, cr, uid, ids, datas, context={}):
        io = StringIO.StringIO()

        date_to_int = lambda x: int(x.ticks())
        int_to_date = lambda x: '/a60{}'+localtime(x).strftime('%d %m %Y')
        gt = GanttCanvas(io, convertors=(date_to_int, int_to_date))

        tasks = pooler.get_pool(cr.dbname).get('project.task').browse(cr, uid, ids)
        tasks, last_date = _compute_tasks(cr, uid, tasks, now())
        for user_id in tasks.keys():
            for t in tasks[user_id]:
                gt.add(t[3], t[2], [(t[0],t[1])])
        try:
            gt.draw()
        except:
            pass
        gt.close()
        self.obj = external_pdf(io.getvalue())
        self.obj.render()
        return (self.obj.pdf, 'pdf')
report_tasks('report.project.tasks.gantt')


class report_projects(report_int):
    def create(self, cr, uid, ids, datas, context={}):
        io = StringIO.StringIO()
        date_to_int = lambda x: int(x.ticks())
        int_to_date = lambda x: '/a60{}'+localtime(x).strftime('%d %m %Y')
        gt = GanttCanvas(io, convertors=(date_to_int, int_to_date))
        tasks, last_date = _project_compute(cr, uid, ids[0])
        for user_id in tasks.keys():
            for t in tasks[user_id]:
                gt.add(t[3], t[2], [(t[0],t[1])])
        try:
            gt.draw()
        except:
            pass
        gt.close()
        self.obj = external_pdf(io.getvalue())
        self.obj.render()
        return (self.obj.pdf, 'pdf')
report_projects('report.project.project.gantt')

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

