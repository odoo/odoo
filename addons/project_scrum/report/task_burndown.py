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

        if 'date_start' not in datas:
            cr.execute('select min(date_start) from project_task where id IN %s',(tuple(ids),))
            dt = cr.fetchone()[0]
            if dt:
                datas['date_start'] = dt[:10]
            else:
                datas['date_start'] = time.strftime('%Y-%m-%d')
        if 'date_stop' not in datas:
            cr.execute('select max(date_start),max(date_end) from project_task where id IN %s',(tuple(ids),))
            res = cr.fetchone()
            datas['date_stop'] = (res[0] and res[0][:10]) or time.strftime('%Y-%m-%d')
            if res[1] and datas['date_stop']<res[1]:
                datas['date_stop'] = res[1][:10]

        datas = _burndown.compute_burndown(cr, uid, ids, datas['date_start'], datas['date_stop'])
        canv = canvas.init(fname=io, format='pdf')
        canv.set_author("OpenERP")

        max_hour = reduce(lambda x,y: max(y[1],x), datas, 0)

        int_to_date = lambda x: '/a60{}' + datetime(time.localtime(x).tm_year, time.localtime(x).tm_mon, time.localtime(x).tm_mday).strftime('%d %m %Y')

        def _interval_get(*args):
            result = set()
            for i in range(20):
                d = time.localtime(datas[0][0] + (((datas[-1][0]-datas[0][0])/20)*(i+1)))
                res = time.mktime(d)
                result.add(res)

            return list(result)

        if datas[-1][0] == datas[0][0]:
            x_range = (datas[0][0],datas[-1][0]+1)
        else:
            x_range = (datas[0][0],datas[-1][0])

        ar = area.T(x_grid_style=line_style.gray50_dash1,
            x_axis=axis.X(label="Date", format=int_to_date),
            y_axis=axis.Y(label="Burndown Chart - Planned Hours"),
            x_grid_interval=_interval_get,
            x_range = x_range,
            y_range = (0,max_hour),
            legend = None,
            size = (680,450))
        ar.add_plot(line_plot.T(data=datas))
        ar.draw(canv)
        canv.close()

        self.obj = _burndown.external_pdf(io.getvalue())
        self.obj.render()
        return (self.obj.pdf,'pdf')
report_tasks('report.project.tasks.burndown')

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

