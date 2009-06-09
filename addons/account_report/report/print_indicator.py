# -*- encoding: utf-8 -*-
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

# -*- encoding: utf-8 -*-
##############################################################################
#
# Copyright (c) 2004-2009 TINY SPRL. (http://tiny.be) All Rights Reserved.
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

#from report.interface import report_int
#from reportlab.graphics.shapes import Drawing
#from reportlab.graphics.charts.barcharts import VerticalBarChart
#import reportlab.lib.colors as colors
#from reportlab.graphics.widgetbase import Widget, TypedPropertyCollection
#from reportlab.graphics.charts.textlabels import BarChartLabel
#from reportlab.graphics import renderPM
#from report.render import render
#from report.interface import report_int
from pychart import *
import StringIO
theme.use_color = 1
theme.default_font_family = "Helvetica-Bold"
theme.default_font_size = 18
theme.default_line_width = 1.0
import tools
import os


class accounting_report_indicator(report_sxw.rml_parse):

    def __init__(self, cr, uid, name, context):
        super(accounting_report_indicator, self).__init__(cr, uid, name, context)
        self.ret_list = []
        self.localcontext.update({
            'time': time,
            'getgraph': self.getgraph,
            'lines':self.lines,
            'getarray':self.getarray,
            'gettree':self.gettree,
            'getarray_head':self.getarray_head,
        })
        self.count = 0
        self.treecount = 0
        self.list = []
        self.header_name = []
        self.header_val = []
        self.main_dict = {}

#

    def lines(self,data):
        res={}
        result=[]
        ind_ids=self.pool.get('account.report.report').search(self.cr,self.uid,[])
        obj_inds=self.pool.get('account.report.report').browse(self.cr,self.uid,ind_ids)

#        def find_child(obj):
#            self.list.append(obj)
#            if obj.child_ids:
#                for child in obj.child_ids:
#                    find_child(child)
#            return True
#
#        find_child(obj_inds)

        for obj_ind in obj_inds:
            level = 0
            res = {
                'id':obj_ind.id,
                'name':obj_ind.name,
                'code':obj_ind.code,
                'expression':obj_ind.expression,
                'disp_graph':obj_ind.disp_graph,
                'disp_tree':obj_ind.disp_tree,
                'note':obj_ind.note,
                'level' : obj_ind.parent_id or 0,
                'type':obj_ind.type,
                'array_table' : False,
                }
            if obj_ind.parent_id:
                for record in result:
                    if record['id'] == obj_ind.parent_id.id:
                        res['level'] = record['level'] + 1
                        break
            if len(obj_ind.expression)>=2:
                res['array_table'] = True
            result.append(res)
        return result

    def getarray_head(self,data,object,array_header=''):
        self.getgraph(data,object,intercall=True)
        self.header_val=[str(x) for x in self.header_val]
        if data['select_base'] == 'year':
            year = [1,2,3,4,5,6,7,8]
            temp_head = [str(x) for x in self.header_name]
            head_dict = dict(zip(year,temp_head))
        else:
            temp_head = [str(x[0:3]) for x in self.header_name]
            head_dict = dict(zip(temp_head,temp_head))
        print "head_dict",head_dict
        return [head_dict]

    def getarray(self,data,object,array_header=''):
        res={}
        result=[]
        self.getgraph(data,object,intercall=True)
        self.header_val = [str(x) for x in self.header_val]
        if data['select_base'] == 'year':
            year = [1,2,3,4,5,6,7,8]
            temp_dict = zip(year,self.header_val)
        else:
            temp_head = [str(x[0:3]) for x in self.header_name]
            temp_dict = zip(temp_head,self.header_val)
        res=dict(temp_dict)
        array_header = eval(array_header,{'year':'Fiscal Year','periods':'Periods'})
        res[array_header]=object['name']
        result.append(res)
        return result

    def gettree(self,data,object):
        pool_history=self.pool.get('account.report.report')
        obj_history=pool_history.browse(self.cr,self.uid,object['id'])
        result=[]
        self.treecount +=1
        path=tools.config['addons_path']+"/account_report/tmp_images/tree_image"

        dirname =tools.config['addons_path']+'/account_report/tmp_images/'
        if not os.path.isdir(dirname):
            os.mkdir(dirname)

        can = canvas.init('tree_image'+str(self.treecount)+".png")

        theme.default_font_size = 12

        self.child_dist=0

        level=0
        self.level=0
        self.child_dist=0

        def draw_tree(obj_history,base_x,base_y,level=0,i=0):
            self.line_y=base_y
            if obj_history.child_ids:
                if self.child_dist:
                    diff=i*self.child_dist
                    self.child_dist=0
                else:
                    diff=i
                if self.level>0 and (base_y-(50*diff)) >= self.level:
                        base_y=self.level-(50*i)
                else:
                    base_y=base_y-(50*diff)
                tb = text_box.T(loc=(base_x,base_y),line_style=line_style.darkblue,text="/hC"+str(obj_history.code)+":\n"+str(obj_history.amount))

                tb.add_arrow((base_x+100,base_y))
                tb.draw()

                if level!=0:
                    a = arrow.T(head_style = 1)
                    a.draw([(base_x-30,base_y), (base_x,base_y)])
                level+=1

                if i>0:
                    can.line(line_style.black,base_x-30,base_y,base_x-30,self.line_y)

                i=0
                for child in obj_history.child_ids:
                    draw_tree(child,base_x+(100),base_y,level,i)
                    i+=1

                child_dist=len(obj_history.child_ids)
                self.child_dist=max(self.child_dist,child_dist)

            else:

                if self.level>0 and  (base_y-(50*i)) >= self.level:
                    base_y=self.level-(50)
                else:
                    base_y=base_y-(50*(i))

                tb12 = text_box.T(loc=(base_x,base_y), text="/hC"+str(obj_history.code)+":\n"+str(obj_history.amount))
                tb12.draw()

                if i>0:
                    can.line(line_style.black,base_x-30,base_y,base_x-30,self.line_y)
                    a = arrow.T(head_style = 1)
                    a.draw([(base_x-30,base_y), (base_x,base_y)])
                self.level=base_y
        self.line_y=900
        draw_tree(obj_history,0,900,0)
        can.close()

        os.system('cp '+'tree_image'+str(self.treecount)+'.png ' +path+str(self.treecount)+'.png')
        os.system('rm '+'tree_image'+str(self.treecount)+'.png')

        return path+str(self.treecount)+'.png'

    def getgraph(self,data,object,intercall=False):
        obj_history=self.pool.get('account.report.history')

        if data['select_base']=='year':
            tuple_search=('fiscalyear_id','in',data['base_selection'][0][2])
            base='year'
        else:
            tuple_search=('period_id','in',data['base_selection'][0][2])
            base='period'

        history_ids=obj_history.search(self.cr,self.uid,[('name','=',object['id']),tuple_search])
        history_ids.sort()
        obj_his=obj_history.browse(self.cr,self.uid,history_ids)

        data_val=[]
        data_period=[]
        if base=='period':
            for item in obj_his:
                data_val.append(item.val)
                data_period.append(item.period_id.name)
        else:
            for i in data['base_selection'][0][2]:
                val_temp=[]
                data_period.append(self.pool.get('account.fiscalyear').browse(self.cr,self.uid,i).name)
                for item in obj_his:
                    if item.fiscalyear_id.id==i:
                        val_temp.append(item.val)
                data_val.append(sum(val_temp))

        self.header_name=data_period
        self.header_val=data_val

        if intercall:
            return True
        self.count +=1
#        drawing = Drawing(400, 300)
#        data = [
#                 tuple(data_val),
#                 ]
#        value_min=0.0
#        vmin=min(data_val)
#        vmax=max(data_val)
#
#        val_min=((vmin < 0.00 and vmin-2.00)  or 0.00)
#        # calculating maximum
#        val_max=(vmax/(pow(10,len(str(int(vmax)))-2))+1)*pow(10,len(str(int(vmax)))-2)
#        bc = VerticalBarChart()
#        bc.x = 50
#        bc.y = 50
#        bc.height = 245
#        bc.width = 300
#        bc.data = data
#        value_step=(abs(val_max)-abs(val_min))/5
#
#        bc.strokeColor = colors.black
#        bc.valueAxis.valueMin = val_min
#        bc.valueAxis.valueMax = val_max
#        bc.valueAxis.valueStep = value_step
#
#        bc.categoryAxis.labels.boxAnchor = 'ne'
#        bc.categoryAxis.labels.dx = 8
#
#        bc.categoryAxis.labels.dy = -2
#        bc.categoryAxis.labels.angle = 30
#        bc.categoryAxis.categoryNames = data_period
#        drawing.add(bc)
#        drawing.save(formats=['png'],fnRoot=path+str(self.count),title="helo")
#        renderPM.drawToFile(drawing1, 'example1.jpg','jpg')
        import os
        path=tools.config['addons_path']+"/account_report/tmp_images/image"

        dirname =tools.config['addons_path']+'/account_report/tmp_images/'
        if not os.path.isdir(dirname):
            os.mkdir(dirname)

        can = canvas.init('image'+str(self.count)+".png")
#        can.clip(0,0,600,400)

        data=zip(self.header_name,self.header_val)

        ar = area.T(size = (650,450),x_coord = category_coord.T(data, 0), y_range = (None, None),
            x_axis = axis.X(label="Period // Year",format="/a-30{}%s"),
            y_axis = axis.Y(label="Value"))

        ar.add_plot(bar_plot.T(data = data,width=15, data_label_format="/o/15{}%s",label = "Value",fill_style=fill_style.red))
        ar.draw()

        can.close()
        os.system('cp '+'image'+str(self.count)+'.png ' +path+str(self.count)+'.png')
        os.system('rm '+'image'+str(self.count)+'.png')
#        can.endclip()
        return path+str(self.count)+'.png'

report_sxw.report_sxw('report.print.indicators', 'account.report.history',
        'addons/account_report/report/print_indicator.rml',
        parser=accounting_report_indicator, header=False)


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

