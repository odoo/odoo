##############################################################################
#
# Copyright (c) 2004-2008 Tiny SPRL (http://tiny.be) All Rights Reserved.
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
###############################################################################
from mx.DateTime import RelativeDateTime, now, DateTime, localtime
from pychart import *
import pychart.legend
from report.misc import choice_colors

#
# Draw a graph
# 
class GanttCanvas(object):
	def __init__(self, io, convertors=(lambda x:x,lambda x:x)):
		self._datas = {}
		self._canvas = canvas.init(fname=io, format='pdf')
		self._canvas.set_author("Tiny ERP")
		self._names = {}
		self._conv = convertors
		self._min = 0
		self._max = 0

	def add(self, user, name, datas):
		if hasattr(user, 'replace'):
			user=user.replace('/', '//')
		if hasattr(name, 'replace'):
			name=name.replace('/', '//')
		if user not in self._datas:
			self._datas[user] = []
		for f in datas:
			x = map(self._conv[0], f)
			if x[0]<self._min or not self._min:
				self._min = x[0]
			if x[1]>self._max or not self._max:
				self._max = x[1]
			self._datas[user].append( (name, x))
			self._names.setdefault(name, x[0])

	def draw(self):
		colors = choice_colors(len(self._datas.keys()))
		user_color = {}
		for user in self._datas.keys():
			user_color[user] = colors.pop()

		names = []
		for n in self._names:
			names.append((self._names[n], n))
		names.sort()
		names.reverse()
		def _interval_get(*args):
			result = []
			for i in range(20):
				d = localtime(self._min + (((self._max-self._min)/20)*(i+1)))
				res = DateTime(d.year, d.month, d.day).ticks()
				if (not result) or result[-1]<>res:
					result.append(res)
			return result

		ar = area.T(y_coord = category_coord.T(names, 1),
			x_grid_style=line_style.gray50_dash1,
			x_grid_interval=_interval_get,
			x_range = (self._min,self._max),
			x_axis=axis.X(label="Date", format=self._conv[1]),
			y_axis=axis.Y(label="Tasks"),
			legend = legend.T(), size = (680,450))

		for user in self._datas:
			chart_object.set_defaults(interval_bar_plot.T, direction="horizontal", data=self._datas[user])
			f = fill_style.Plain()
			f.bgcolor = user_color[user]
			ar.add_plot(interval_bar_plot.T(fill_styles = [f, None], label=user, cluster=(0,1)))

		ar.draw(self._canvas)

	def close(self):
		self._canvas.close()

if __name__ == '__main__':
	date_to_int = lambda x: int(x.ticks())
	int_to_date = lambda x: '/a60{}'+localtime(x).strftime('%d %m %Y')
	gt = GanttCanvas('test.pdf', convertors=(date_to_int, int_to_date))
	gt.add('nicoe', 'Graphe de gantt', [(DateTime(2005,6,12), DateTime(2005,6,13))])
	gt.add('nicoe', 'Tarifs', [(DateTime(2005,6,19), DateTime(2005,6,21))])
	gt.add('gaetan', 'Calcul des prix', [(DateTime(2005,6,12), DateTime(2005,6,13))])
	gt.add('nico', 'Mise a jour du site', [(DateTime(2005,6,13), DateTime(2005,6,16))])
	gt.add('tom', 'Coucou', [(DateTime(2005,6,11), DateTime(2005,6,12))])
	gt.draw()
	gt.close()
