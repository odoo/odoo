# -*- encoding: utf-8 -*-
##############################################################################
#
# Copyright (c) 2004-2008 TINY SPRL. (http://tiny.be) All Rights Reserved.
#
# $Id$
#
# WARNING: This program as such is intended to be used by professional
# programmers who take the whole responsability of assessing all potential
# consequences resulting from its eventual inadequacies and bugs
# End users who are looking for a ready-to-use solution with commercial
# garantees and support are strongly adviced to contract a Free Software
# Service Company
#
# This program is Free Software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA  02111-1307, USA.
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

