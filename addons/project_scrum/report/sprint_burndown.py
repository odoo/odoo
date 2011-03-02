# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
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

import StringIO
import pooler

from report.render import render
from report.interface import report_int

from datetime import datetime
import time

from pychart import *
import pychart.legend

import _burndown
class report_tasks(report_int):
    def create(self, cr, uid, ids, datas, context=None):
        if context is None:
            context = {}
        io = StringIO.StringIO()

        canv = canvas.init(fname=io, format='pdf')
        canv.set_author("OpenERP")
        canv.set_title("Burndown Chart")
        pool = pooler.get_pool(cr.dbname)
        sprint_pool = pool.get('project.scrum.sprint')
        task_pool = pool.get('project.task')
        # For add the report header on the top of the report.
        tb = text_box.T(loc=(320, 500), text="/hL/15/bBurndown Chart", line_style=None)
        tb.draw()
        int_to_date = lambda x: '/a60{}' + datetime(time.localtime(x).tm_year, time.localtime(x).tm_mon, time.localtime(x).tm_mday).strftime('%d %m %Y')
        for sprint in sprint_pool.browse(cr, uid, ids, context=context):
            task_ids = task_pool.search(cr, uid, [('sprint_id','=',sprint.id)], context=context)
            datas = _burndown.compute_burndown(cr, uid, task_ids, sprint.date_start, sprint.date_stop)
            max_hour = reduce(lambda x,y: max(y[1],x), datas, 0) or None 
            def _interval_get(*args):
                result = []
                for i in range(20):
                    d = time.localtime(datas[0][0] + (((datas[-1][0]-datas[0][0])/20)*(i+1)))
                    res = time.mktime(d)
                    if (not result) or result[-1]<>res:
                        result.append(res)
                return result

            guideline__data=[(datas[0][0],max_hour), (datas[-1][0],0)]

            ar = area.T(x_grid_style=line_style.gray50_dash1,
                x_axis=axis.X(label="Date", format=int_to_date),
                y_axis=axis.Y(label="Burndown Chart - Planned Hours"),
                x_grid_interval=_interval_get,
                x_range = (datas[0][0],datas[-1][0]),
                y_range = (0,max_hour),
                legend = None,
                size = (680,450))
            ar.add_plot(line_plot.T(data=guideline__data, line_style=line_style.red))
            ar.add_plot(line_plot.T(data=datas, line_style=line_style.green))

            entr1 = pychart.legend.Entry(label="guideline", line_style=line_style.red)
            entr2 = pychart.legend.Entry(label="burndownchart",line_style=line_style.green)
            legend = pychart.legend.T(nr_rows=2, inter_row_sep=5)
            legend.draw(ar,[entr1,entr2],canv)

            ar.draw(canv)
        canv.close()

        self.obj = _burndown.external_pdf(io.getvalue())
        self.obj.render()
        return (self.obj.pdf, 'pdf')
report_tasks('report.scrum.sprint.burndown')

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

