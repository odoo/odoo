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

from openerp.report.render import render
from openerp.report.interface import report_int
import time
from datetime import date, datetime, timedelta
from dateutil.relativedelta import relativedelta

from openerp.report.misc import choice_colors

import StringIO

from pychart import *

theme.use_color = 1

#
# TODO: Bad code, seems buggy, TO CHECK !
#

class external_pdf(render):
    def __init__(self, pdf):
        render.__init__(self)
        self.pdf = pdf
        self.output_type='pdf'

    def _render(self):
        return self.pdf

class report_custom(report_int):
    def _compute_dates(self, time_unit, start, stop):
        if not stop:
            stop = start
        if time_unit == 'month':
            dates = {}
            a = int(start.split("-")[0])*12 + int(start.split("-")[1])
            z = int(stop.split("-")[0])*12 + int(stop.split("-")[1]) + 1
            for i in range(a,z):
                year = i/12
                month = i%12
                if month == 0:
                    year -= 1
                    month = 12
                months = {1:"January",2:"February",3:"March",4:"April",5:"May",6:"June",7:"July",8:"August",9:"September",10:"October",11:"November",12:"December"}
                dates[i] = {
                    'name' :months[month],
                    'start':(datetime(year, month, 2) + relativedelta(day=1)).strftime('%Y-%m-%d'),
                    'stop' :(datetime(year, month, 2) + relativedelta(day=31)).strftime('%Y-%m-%d'),
                }
            return dates
        elif time_unit == 'week':
            dates = {}
            start_week = date(int(start.split("-")[0]),int(start.split("-")[1]),int(start.split("-")[2])).isocalendar()
            end_week = date(int(stop.split("-")[0]),int(stop.split("-")[1]),int(stop.split("-")[2])).isocalendar()
            a = int(start.split("-")[0])*52 + start_week[1]
            z = int(stop.split("-")[0])*52 + end_week[1]
            for i in range(a,z+1):
                year = i/52
                week = i%52
                d = date(year, 1, 1)

                dates[i] = {
                    'name' :"Week #%d" % week,
                    'start':(d + timedelta(days=-d.weekday(), weeks=week)).strftime('%Y-%m-%d'),
                    'stop' :(d + timedelta(days=6-d.weekday(), weeks=week)).strftime('%Y-%m-%d'),
                }
            return dates
        else: # time_unit = day
            dates = {}
            a = datetime(int(start.split("-")[0]),int(start.split("-")[1]),int(start.split("-")[2]))
            z = datetime(int(stop.split("-")[0]),int(stop.split("-")[1]),int(stop.split("-")[2]))
            i = a
            while i <= z:
                dates[map(int,i.strftime('%Y%m%d').split())[0]] = {
                    'name' :i.strftime('%Y-%m-%d'),
                    'start':i.strftime('%Y-%m-%d'),
                    'stop' :i.strftime('%Y-%m-%d'),
                }
                i = i + relativedelta(days=+1)
            return dates
        return {}

    def create(self, cr, uid, ids, datas, context=None):
        assert len(ids), 'You should provide some ids!'
        colors = choice_colors(len(ids))
        cr.execute(
            "SELECT MAX(mrp_production.date_planned) AS stop,MIN(mrp_production.date_planned) AS start "\
            "FROM mrp_workcenter, mrp_production, mrp_production_workcenter_line "\
            "WHERE mrp_production_workcenter_line.production_id=mrp_production.id "\
            "AND mrp_production_workcenter_line.workcenter_id=mrp_workcenter.id "\
            "AND mrp_production.state NOT IN ('cancel','done') "\
            "AND mrp_workcenter.id IN %s",(tuple(ids),))
        res = cr.dictfetchone()
        if not res['stop']:
            res['stop'] = time.strftime('%Y-%m-%d %H:%M:%S')
        if not res['start']:
            res['start'] = time.strftime('%Y-%m-%d %H:%M:%S')
        dates = self._compute_dates(datas['form']['time_unit'], res['start'][:10], res['stop'][:10])
        dates_list = dates.keys()
        dates_list.sort()
        x_index = []
        for date in dates_list:
            x_index.append((dates[date]['name'], date))
        pdf_string = StringIO.StringIO()
        can = canvas.init(fname=pdf_string, format='pdf')
        can.set_title("Work Center Loads")
        chart_object.set_defaults(line_plot.T, line_style=None)
        if datas['form']['measure_unit'] == 'cycles':
            y_label = "Load (Cycles)"
        else:
            y_label = "Load (Hours)"

        # For add the report header on the top of the report.
        tb = text_box.T(loc=(300, 500), text="/hL/15/bWork Center Loads", line_style=None)
        tb.draw()
        ar = area.T(legend = legend.T(),
                    x_grid_style = line_style.gray70_dash1,
                    x_axis = axis.X(label="Periods", format="/a90/hC%s"),
                    x_coord = category_coord.T(x_index, 0),
                    y_axis = axis.Y(label=y_label),
                    y_range = (0, None),
                    size = (640,480))
        bar_plot.fill_styles.reset();
        # select workcenters
        cr.execute(
            "SELECT mw.id, rs.name FROM mrp_workcenter mw, resource_resource rs " \
            "WHERE mw.id IN %s and mw.resource_id=rs.id " \
            "ORDER BY mw.id" ,(tuple(ids),))
        workcenters = cr.dictfetchall()

        data = []
        for date in dates_list:
            vals = []
            for workcenter in workcenters:
                cr.execute("SELECT SUM(mrp_production_workcenter_line.hour) AS hours, SUM(mrp_production_workcenter_line.cycle) AS cycles, \
                                resource_resource.name AS name, mrp_workcenter.id AS id \
                            FROM mrp_production_workcenter_line, mrp_production, mrp_workcenter, resource_resource \
                            WHERE (mrp_production_workcenter_line.production_id=mrp_production.id) \
                                AND (mrp_production_workcenter_line.workcenter_id=mrp_workcenter.id) \
                                AND (mrp_workcenter.resource_id=resource_resource.id) \
                                AND (mrp_workcenter.id=%s) \
                                AND (mrp_production.date_planned BETWEEN %s AND %s) \
                            GROUP BY mrp_production_workcenter_line.workcenter_id, resource_resource.name, mrp_workcenter.id \
                            ORDER BY mrp_workcenter.id", (workcenter['id'], dates[date]['start'] + ' 00:00:00', dates[date]['stop'] + ' 23:59:59'))
                res = cr.dictfetchall()
                if not res:
                    vals.append(0.0)
                else:
                    if datas['form']['measure_unit'] == 'cycles':
                        vals.append(res[0]['cycles'] or 0.0)
                    else:
                        vals.append(res[0]['hours'] or 0.0)

            toto = [dates[date]['name']]
            for val in vals:
                toto.append(val)
            data.append(toto)

        workcenter_num = 0
        for workcenter in workcenters:
            f = fill_style.Plain()
            f.bgcolor = colors[workcenter_num]
            ar.add_plot(bar_plot.T(label=workcenter['name'], data=data, fill_style=f, hcol=workcenter_num+1, cluster=(workcenter_num, len(res))))
            workcenter_num += 1

        if (not data) or (len(data[0]) <= 1):
            ar = self._empty_graph(time.strftime('%Y-%m-%d'))
        ar.draw(can)
        # close canvas so that the file is written to "disk"
        can.close()
        self.obj = external_pdf(pdf_string.getvalue())
        self.obj.render()
        pdf_string.close()
        return (self.obj.pdf, 'pdf')

    def _empty_graph(self, date):
        data = [[date, 0]]
        ar = area.T(x_coord = category_coord.T(data, 0), y_range = (0, None),
                    x_axis = axis.X(label="Periods"),
                    y_axis = axis.Y(label="Load"))
        ar.add_plot(bar_plot.T(data = data, label="No production order"))
        return ar

report_custom('report.mrp.workcenter.load')


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

