##############################################################################
#
# Copyright (c) 2006 TINY SPRL. (http://tiny.be) All Rights Reserved.
#                    Fabien Pinckaers <fp@tiny.Be>
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

from report.render import render 
from report.interface import report_int
from pychart import *
from mx.DateTime import *
from report.misc import choice_colors
import time, mx
import random
import StringIO


theme.use_color = 1
#theme.scale = 2
random.seed(0)

class external_pdf(render):
	def __init__(self, pdf):
		render.__init__(self)
		self.pdf = pdf
		self.output_type='pdf'
		
	def _render(self):
		return self.pdf

class report_custom(report_int):
	def _compute_dates(self, time_unit, start, stop=False):
		if not stop:
			stop = start
		dates = {}
		if time_unit == 'month':
			a = Date(*map(int, start.split("-"))).year*12+Date(*map(int, start.split("-"))).month
			z = Date(*map(int,  stop.split("-"))).year*12+Date(*map(int,  stop.split("-"))).month+1
			for i in range(a,z):
				year = i/12
				month = i%12
				if month == 0:
					year -= 1
					month = 12
				months = { 1:"January",2:"February",3:"March",4:"April",5:"May",6:"June",7:"July",8:"August",9:"September",10:"October",11:"November",12:"December" }
				dates[i] = {
					'name' :months[month],
					'start':(Date(year, month, 2) + RelativeDateTime(day=1)).strftime('%Y-%m-%d'),
					'stop' :(Date(year, month, 2) + RelativeDateTime(day=-1)).strftime('%Y-%m-%d'),
				}
			return dates
		elif time_unit == 'week':
			a = Date(*map(int, start.split("-"))).iso_week[0]*52+Date(*map(int, start.split("-"))).iso_week[1]
			z = Date(*map(int,  stop.split("-"))).iso_week[0]*52+Date(*map(int,  stop.split("-"))).iso_week[1]
			for i in range(a,z+1):
				year = i/52
				week = i%52
				dates[i] = {
					'name' :"Week #%d" % week,
					'start':ISO.WeekTime(year, week, 1).strftime('%Y-%m-%d'),
					'stop' :ISO.WeekTime(year, week, 7).strftime('%Y-%m-%d'),
				}
			return dates
		else: # time_unit = day
			a = Date(*map(int, start.split("-")))
			z = Date(*map(int, stop.split("-")))
			i = a
			while i <= z:
				dates[map(int,i.strftime('%Y%m%d').split())[0]] = {
					'name' :i.strftime('%Y-%m-%d'),
					'start':i.strftime('%Y-%m-%d'),
					'stop' :i.strftime('%Y-%m-%d'),
				}
				i = i + RelativeDateTime(days=+1)
			return dates
		return {}

	def create(self, cr, uid, ids, datas, context={}):
		datas = datas['form']
		if datas['users_id']:
			datas['users_id'] = datas['users_id'][0][2]
		else:
			cr.execute('select id from res_users limit 10')
			datas['users_id'] = [x[0] for x in cr.fetchall()]
		cr.execute('select id,name from res_users where id in ('+','.join(map(str,datas['users_id']))+')')
		users_name = dict(cr.fetchall())
		colors = choice_colors(len(datas['users_id']))
		dates = self._compute_dates(datas['type'], datas['date1'], datas['date2'])
		dates_list = dates.keys()
		dates_list.sort()
		x_index = map(lambda x: (dates[x]['name'],x), dates_list)
		pdf_string = StringIO.StringIO()
		can = canvas.init(fname=pdf_string, format='pdf')
		chart_object.set_defaults(line_plot.T, line_style=None)
		y_label = 'Number of Objects'

		ar = area.T(legend		= legend.T(),
					x_grid_style= line_style.gray70_dash1,
					x_axis		= axis.X(label=None, format="/a90/hC%s"),
					x_coord		= category_coord.T(x_index, 0),
					y_axis		= axis.Y(label=y_label),
					y_range		= (0, None), size = (680,450))
		bar_plot.fill_styles.reset();

		data = []
		for date in dates_list:
			cr.execute(("SELECT create_uid,count(*) FROM %s WHERE (substring(create_date,0,11) BETWEEN '%s' AND '%s') and id in ("+','.join(map(str,datas['users_id']))+") GROUP BY create_uid") % (datas['model'].replace('.','_'), dates[date]['start'], dates[date]['stop']))
			res = dict(cr.fetchall())

			vals = [dates[date]['name']]
			for user in datas['users_id']:
				vals.append(res.get(user, 0.0))
			data.append(vals)

		for user_id in range(len(datas['users_id'])):
			user = datas['users_id'][user_id]

			f = fill_style.Plain()
			f.bgcolor = colors[user_id]
			ar.add_plot(bar_plot.T(label=users_name.get(user,'Unknown'), data=data, hcol=user_id+1, cluster=(user_id, len(datas['users_id'])), fill_style=f ))

		ar.draw(can)
		can.close()
		self.obj = external_pdf(pdf_string.getvalue())
		self.obj.render()
		pdf_string.close()
		return (self.obj.pdf, 'pdf')
report_custom('report.productivity_analysis.report')

