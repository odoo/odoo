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

import pooler
import time
from report import report_sxw
from crm.report import report_businessopp
from report.interface import report_int
from reportlab.graphics.shapes import Drawing
from reportlab.graphics.charts.barcharts import VerticalBarChart
import reportlab.lib.colors as colors
#from reportlab.graphics import renderPM
import tools

class accounting_report1(report_sxw.rml_parse):

    def __init__(self, cr, uid, name, context):
        super(accounting_report1, self).__init__(cr, uid, name, context)
        self.ret_list = []
        self.localcontext.update({
            'time': time,
            'test': self.test1,
            'lines':self.lines,
        })
        self.count=0

    def lines(self,data):
        res={}
        result=[]
        obj_ind=self.pool.get('account.report.report').browse(self.cr,self.uid,data['indicator_id'])
        res = {
            'name':obj_ind.name,
            'code':obj_ind.code,
            'expression':obj_ind.expression,
            'disp_graph':obj_ind.disp_graph,
            'note':obj_ind.note,
            'type':obj_ind.type
            }
        result.append(res)
        return result

    def test1(self):
        self.count +=1
        drawing = Drawing(400, 200)
        data = [
                 (13, 5, 20, 22, 37, 45, 19, 4,11,-5),
                 ]
        bc = VerticalBarChart()
        bc.x = 50
        bc.y = 50
        bc.height = 155
        bc.width = 300
        bc.data = data
        bc.strokeColor = colors.black
        bc.valueAxis.valueMin = 0
        bc.valueAxis.valueMax = 50
        bc.valueAxis.valueStep = 10

        bc.categoryAxis.labels.boxAnchor = 'ne'
        bc.categoryAxis.labels.dx = 8
#        bc.barWidth=5
        bc.categoryAxis.labels.dy = -2
        bc.categoryAxis.labels.angle = 30
        bc.categoryAxis.categoryNames = ['Jan-99','Feb-99','Mar-99',
               'Apr-99','May-99','Jun-99','Jul-99','Aug-99','kkk','fff']
        drawing.add(bc)
        drawing.save(formats=['png'],fnRoot=tools.config['root_path']+"/Temp_report/Image"+str(self.count),title="helo")
#        renderPM.drawToFile(drawing1, 'example1.jpg','jpg')
        return tools.config['root_path']+"/Temp_report/Image"+str(self.count)+'.png'


report_sxw.report_sxw('report.print.indicators', 'account.report.history',
        'addons/account_report/report/print_indicator.rml',
        parser=accounting_report1, header=False)


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
