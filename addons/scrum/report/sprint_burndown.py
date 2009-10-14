# -*- coding: utf-8 -*-
##############################################################################
#    
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2009 Tiny SPRL (<http://tiny.be>).
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

from mx import DateTime
import time

from pychart import *
import pychart.legend

import _burndown

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

        canv = canvas.init(fname=io, format='pdf')
        canv.set_author("Open ERP")

        cr.execute('select id,date_start,date_stop from scrum_sprint where id=%s', (datas['id'],))
        for (id,date_start,date_stop) in cr.fetchall():
            date_to_int = lambda x: int(x.ticks())
            int_to_date = lambda x: '/a60{}'+DateTime.localtime(x).strftime('%d/%m/%Y')

            cr.execute('select id from project_task where product_backlog_id in(select id from scrum_product_backlog where sprint_id=%s)', (id,))

            ids = map(lambda x: x[0], cr.fetchall())
            datas = _burndown.compute_burndown(cr, uid, ids, date_start, date_stop)

            max_hour = reduce(lambda x,y: max(y[1],x), datas, 0)

            date_to_int = lambda x: int(x.ticks())
            int_to_date = lambda x: '/a60{}'+DateTime.localtime(x).strftime('%d %m %Y')

            def _interval_get(*args):
                result = []
                for i in range(20):
                    d = DateTime.localtime(datas[0][0] + (((datas[-1][0]-datas[0][0])/20)*(i+1)))
                    res = DateTime.DateTime(d.year, d.month, d.day).ticks()
                    if (not result) or result[-1]<>res:
                        result.append(res)
                return result

            ar = area.T(x_grid_style=line_style.gray50_dash1,
                x_axis=axis.X(label="Date", format=int_to_date),
                y_axis=axis.Y(label="Burndown Chart - Planned Hours"),
                x_grid_interval=_interval_get,
                x_range = (datas[0][0],datas[-1][0]),
                y_range = (0,max_hour),
                legend = None,
                size = (680,450))
            ar.add_plot(line_plot.T(data=datas))
            ar.draw(canv)
        canv.close()

        self.obj = external_pdf(io.getvalue())
        self.obj.render()
        return (self.obj.pdf, 'pdf')
report_tasks('report.scrum.sprint.burndown')

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

