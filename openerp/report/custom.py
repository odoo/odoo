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

import os
import time
import openerp.netsvc as netsvc

import openerp.tools as tools
from openerp.tools.safe_eval import safe_eval as eval
import print_xml
import render
from interface import report_int
import common
from openerp.osv.osv import except_osv
from openerp.osv.orm import browse_null
from openerp.osv.orm import browse_record_list
import openerp.pooler as pooler
from pychart import *
import misc
import cStringIO
from lxml import etree
from openerp.tools.translate import _

class external_pdf(render.render):
    def __init__(self, pdf):
        render.render.__init__(self)
        self.pdf = pdf
        self.output_type='pdf'
    def _render(self):
        return self.pdf

theme.use_color = 1


#TODO: devrait heriter de report_rml a la place de report_int 
# -> pourrait overrider que create_xml a la place de tout create
# heuu, ca marche pas ds tous les cas car graphs sont generes en pdf directment
# par pychart, et on passe donc pas par du rml
class report_custom(report_int):
    def __init__(self, name):
        report_int.__init__(self, name)
    #
    # PRE:
    #    fields = [['address','city'],['name'], ['zip']]
    #    conditions = [[('zip','==','3'),(,)],(,),(,)] #same structure as fields
    #    row_canvas = ['Rue', None, None]
    # POST:
    #    [ ['ville','name','zip'] ]
    #
    def _row_get(self, cr, uid, objs, fields, conditions, row_canvas=None, group_by=None):
        result = []
        tmp = []
        for obj in objs:
            tobreak = False
            for cond in conditions:
                if cond and cond[0]:
                    c = cond[0]
                    temp = c[0](eval('obj.'+c[1],{'obj': obj}))
                    if not eval('\''+temp+'\''+' '+c[2]+' '+'\''+str(c[3])+'\''):
                        tobreak = True
            if tobreak:
                break
            levels = {}
            row = []
            for i in range(len(fields)):
                if not fields[i]:
                    row.append(row_canvas and row_canvas[i])
                    if row_canvas[i]:
                        row_canvas[i]=False
                elif len(fields[i])==1:
                    if not isinstance(obj, browse_null):
                        row.append(str(eval('obj.'+fields[i][0],{'obj': obj})))
                    else:
                        row.append(None)
                else:
                    row.append(None)
                    levels[fields[i][0]]=True
            if not levels:
                result.append(row)
            else:
                # Process group_by data first
                key = []
                if group_by != None and fields[group_by] != None:
                    if fields[group_by][0] in levels.keys():
                        key.append(fields[group_by][0])
                    for l in levels.keys():
                        if l != fields[group_by][0]:
                            key.append(l)
                else:
                    key = levels.keys()
                for l in key:
                    objs = eval('obj.'+l,{'obj': obj})
                    if not isinstance(objs, browse_record_list) and type(objs) <> type([]):
                        objs = [objs]
                    field_new = []
                    cond_new = []
                    for f in range(len(fields)):
                        if (fields[f] and fields[f][0])==l:
                            field_new.append(fields[f][1:])
                            cond_new.append(conditions[f][1:])
                        else:
                            field_new.append(None)
                            cond_new.append(None)
                    if len(objs):
                        result += self._row_get(cr, uid, objs, field_new, cond_new, row, group_by)
                    else:
                        result.append(row)
        return result 


    def create(self, cr, uid, ids, datas, context=None):
        if not context:
            context={}
        self.pool = pooler.get_pool(cr.dbname)
        report = self.pool.get('ir.report.custom').browse(cr, uid, [datas['report_id']])[0]
        datas['model'] = report.model_id.model
        if report.menu_id:
            ids = self.pool.get(report.model_id.model).search(cr, uid, [])
            datas['ids'] = ids

        report_id = datas['report_id']
        report = self.pool.get('ir.report.custom').read(cr, uid, [report_id], context=context)[0]
        fields = self.pool.get('ir.report.custom.fields').read(cr, uid, report['fields_child0'], context=context)

        fields.sort(lambda x,y : x['sequence'] - y['sequence'])

        if report['field_parent']:
            parent_field = self.pool.get('ir.model.fields').read(cr, uid, [report['field_parent'][0]], ['model'])
        model_name = self.pool.get('ir.model').read(cr, uid, [report['model_id'][0]], ['model'], context=context)[0]['model']

        fct = {}
        fct['id'] = lambda x : x
        fct['gety'] = lambda x: x.split('-')[0]
        fct['in'] = lambda x: x.split(',')
        new_fields = []
        new_cond = []
        for f in fields:
            row = []
            cond = []
            for i in range(4):
                field_child = f['field_child'+str(i)]
                if field_child:
                    row.append(
                        self.pool.get('ir.model.fields').read(cr, uid, [field_child[0]], ['name'], context=context)[0]['name']
                    )
                    if f['fc'+str(i)+'_operande']:
                        fct_name = 'id'
                        cond_op =  f['fc'+str(i)+'_op']
                        if len(f['fc'+str(i)+'_op'].split(',')) == 2:
                            cond_op =  f['fc'+str(i)+'_op'].split(',')[1]
                            fct_name = f['fc'+str(i)+'_op'].split(',')[0]
                        cond.append((fct[fct_name], f['fc'+str(i)+'_operande'][1], cond_op, f['fc'+str(i)+'_condition']))
                    else:
                        cond.append(None)
            new_fields.append(row)
            new_cond.append(cond)
        objs = self.pool.get(model_name).browse(cr, uid, ids)

        # Group by
        groupby = None
        idx = 0
        for f in fields:
            if f['groupby']:
                groupby = idx
            idx += 1


        results = []
        if report['field_parent']:
            level = []
            def build_tree(obj, level, depth):
                res = self._row_get(cr, uid,[obj], new_fields, new_cond)
                level.append(depth)
                new_obj = eval('obj.'+report['field_parent'][1],{'obj': obj})
                if not isinstance(new_obj, list) :
                    new_obj = [new_obj]
                for o in  new_obj:
                    if not isinstance(o, browse_null):
                        res += build_tree(o, level, depth+1)
                return res

            for obj in objs:
                results += build_tree(obj, level, 0)
        else:
            results = self._row_get(cr, uid,objs, new_fields, new_cond, group_by=groupby)

        fct = {
            'calc_sum': lambda l: reduce(lambda x,y: float(x)+float(y), filter(None, l), 0),
            'calc_avg': lambda l: reduce(lambda x,y: float(x)+float(y), filter(None, l), 0) / (len(filter(None, l)) or 1.0),
            'calc_max': lambda l: reduce(lambda x,y: max(x,y), [(i or 0.0) for i in l], 0),
            'calc_min': lambda l: reduce(lambda x,y: min(x,y), [(i or 0.0) for i in l], 0),
            'calc_count': lambda l: len(filter(None, l)),
            'False': lambda l: '\r\n'.join(filter(None, l)),
            'groupby': lambda l: reduce(lambda x,y: x or y, l)
        }
        new_res = []

        prev = None
        if groupby != None:
            res_dic = {}
            for line in results:
                if not line[groupby] and prev in res_dic:
                    res_dic[prev].append(line)
                else:
                    prev = line[groupby]
                    if res_dic.has_key(line[groupby]):
                        res_dic[line[groupby]].append(line)
                    else:
                        res_dic[line[groupby]] = []
                        res_dic[line[groupby]].append(line)
            #we use the keys in results since they are ordered, whereas in res_dic.heys() they aren't
            for key in filter(None, [x[groupby] for x in results]):
                row = []
                for col in range(len(fields)):
                    if col == groupby:
                        row.append(fct['groupby'](map(lambda x: x[col], res_dic[key])))
                    else:
                        row.append(fct[str(fields[col]['operation'])](map(lambda x: x[col], res_dic[key])))
                new_res.append(row)
            results = new_res
        
        if report['type']=='table':
            if report['field_parent']:
                res = self._create_tree(uid, ids, report, fields, level, results, context)
            else:
                sort_idx = 0
                for idx in range(len(fields)):
                    if fields[idx]['name'] == report['sortby']:
                        sort_idx = idx
                        break
                try :
                    results.sort(lambda x,y : cmp(float(x[sort_idx]),float(y[sort_idx])))
                except :
                    results.sort(lambda x,y : cmp(x[sort_idx],y[sort_idx]))
                if report['limitt']:
                    results = results[:int(report['limitt'])]
                res = self._create_table(uid, ids, report, fields, None, results, context)
        elif report['type'] in ('pie','bar', 'line'):
            results2 = []
            prev = False
            for r in results:
                row = []
                for j in range(len(r)):
                    if j == 0 and not r[j]:
                        row.append(prev)
                    elif j == 0 and r[j]:
                        prev = r[j]
                        row.append(r[j])
                    else:
                        try:
                            row.append(float(r[j]))
                        except:
                            row.append(r[j])
                results2.append(row)
            if report['type']=='pie':
                res = self._create_pie(cr,uid, ids, report, fields, results2, context)
            elif report['type']=='bar':
                res = self._create_bars(cr,uid, ids, report, fields, results2, context)
            elif report['type']=='line':
                res = self._create_lines(cr,uid, ids, report, fields, results2, context)
        return (self.obj.get(), 'pdf')

    def _create_tree(self, uid, ids, report, fields, level, results, context):
        pageSize=common.pageSize.get(report['print_format'], [210.0,297.0])
        if report['print_orientation']=='landscape':
            pageSize=[pageSize[1],pageSize[0]]

        new_doc = etree.Element('report')
        
        config = etree.SubElement(new_doc, 'config')

        def _append_node(name, text):
            n = etree.SubElement(config, name)
            n.text = text

        _append_node('date', time.strftime('%d/%m/%Y'))
        _append_node('PageFormat', '%s' % report['print_format'])
        _append_node('PageSize', '%.2fmm,%.2fmm' % tuple(pageSize))
        _append_node('PageWidth', '%.2f' % (pageSize[0] * 2.8346,))
        _append_node('PageHeight', '%.2f' %(pageSize[1] * 2.8346,))

        length = pageSize[0]-30-reduce(lambda x,y:x+(y['width'] or 0), fields, 0)
        count = 0
        for f in fields:
            if not f['width']: count+=1
        for f in fields:
            if not f['width']:
                f['width']=round((float(length)/count)-0.5)

        _append_node('tableSize', '%s' %  ','.join(map(lambda x: '%.2fmm' % (x['width'],), fields)))
        _append_node('report-header', '%s' % (report['title'],))
        _append_node('report-footer', '%s' % (report['footer'],))

        header = etree.SubElement(new_doc, 'header')
        for f in fields:
            field = etree.SubElement(header, 'field')
            field.text = f['name']

        lines = etree.SubElement(new_doc, 'lines')
        level.reverse()
        for line in results:
            shift = level.pop()
            node_line = etree.SubElement(lines, 'row')
            prefix = '+'
            for f in range(len(fields)):
                col = etree.SubElement(node_line, 'col')
                if f == 0:
                    col.attrib.update(para='yes',
                                      tree='yes',
                                      space=str(3*shift)+'mm')
                if line[f] != None:
                    col.text = prefix+str(line[f]) or ''
                else:
                    col.text = '/'
                prefix = ''

        transform = etree.XSLT(
            etree.parse(os.path.join(tools.config['root_path'],
                                     'addons/base/report/custom_new.xsl')))
        rml = etree.tostring(transform(new_doc))

        self.obj = render.rml(rml)
        self.obj.render()
        return True


    def _create_lines(self, cr, uid, ids, report, fields, results, context):
        pool = pooler.get_pool(cr.dbname)
        pdf_string = cStringIO.StringIO()
        can = canvas.init(fname=pdf_string, format='pdf')
        
        can.show(80,380,'/16/H'+report['title'])
        
        ar = area.T(size=(350,350),
        #x_coord = category_coord.T(['2005-09-01','2005-10-22'],0),
        x_axis = axis.X(label = fields[0]['name'], format="/a-30{}%s"),
        y_axis = axis.Y(label = ', '.join(map(lambda x : x['name'], fields[1:]))))
        
        process_date = {}
        process_date['D'] = lambda x : reduce(lambda xx,yy : xx+'-'+yy,x.split('-')[1:3])
        process_date['M'] = lambda x : x.split('-')[1]
        process_date['Y'] = lambda x : x.split('-')[0]

        order_date = {}
        order_date['D'] = lambda x : time.mktime((2005,int(x.split('-')[0]), int(x.split('-')[1]),0,0,0,0,0,0))
        order_date['M'] = lambda x : x
        order_date['Y'] = lambda x : x

        abscissa = []
        tmp = {}
        
        idx = 0 
        date_idx = None
        fct = {}
        for f in fields:
            field_id = (f['field_child3'] and f['field_child3'][0]) or (f['field_child2'] and f['field_child2'][0]) or (f['field_child1'] and f['field_child1'][0]) or (f['field_child0'] and f['field_child0'][0])
            if field_id:
                type = pool.get('ir.model.fields').read(cr, uid, [field_id],['ttype'])
                if type[0]['ttype'] == 'date':
                    date_idx = idx
                    fct[idx] = process_date[report['frequency']] 
                else:
                    fct[idx] = lambda x : x
            else:
                fct[idx] = lambda x : x
            idx+=1

        # plots are usually displayed year by year
        # so we do so if the first field is a date
        data_by_year = {}
        if date_idx != None:
            for r in results:
                key = process_date['Y'](r[date_idx])
                if not data_by_year.has_key(key):
                    data_by_year[key] = []
                for i in range(len(r)):
                    r[i] = fct[i](r[i])
                data_by_year[key].append(r)
        else:
            data_by_year[''] = results

        idx0 = 0
        nb_bar = len(data_by_year)*(len(fields)-1)
        colors = map(lambda x:line_style.T(color=x), misc.choice_colors(nb_bar))
        abscissa = {}
        for line in data_by_year.keys():
            fields_bar = []
            # sum data and save it in a list. An item for a fields
            for d in data_by_year[line]:
                for idx in range(len(fields)-1):
                    fields_bar.append({})
                    if fields_bar[idx].has_key(d[0]):
                        fields_bar[idx][d[0]] += d[idx+1]
                    else:
                        fields_bar[idx][d[0]] = d[idx+1]
            for idx  in range(len(fields)-1):
                data = {}
                for k in fields_bar[idx].keys():
                    if data.has_key(k):
                        data[k] += fields_bar[idx][k]
                    else:
                        data[k] = fields_bar[idx][k]
                data_cum = []
                prev = 0.0
                keys = data.keys()
                keys.sort()
                # cumulate if necessary
                for k in keys:
                    data_cum.append([k, float(data[k])+float(prev)])
                    if fields[idx+1]['cumulate']:
                        prev += data[k]
                idx0 = 0
                plot = line_plot.T(label=fields[idx+1]['name']+' '+str(line), data = data_cum, line_style=colors[idx0*(len(fields)-1)+idx])
                ar.add_plot(plot)
                abscissa.update(fields_bar[idx])
                idx0 += 1
        
        abscissa = map(lambda x : [x, None], abscissa)
        ar.x_coord = category_coord.T(abscissa,0)
        ar.draw(can)

        can.close()
        self.obj = external_pdf(pdf_string.getvalue())
        self.obj.render()
        pdf_string.close()
        return True



    def _create_bars(self, cr, uid, ids, report, fields, results, context):
        pool = pooler.get_pool(cr.dbname)
        pdf_string = cStringIO.StringIO()
        can = canvas.init(fname=pdf_string, format='pdf')
        
        can.show(80,380,'/16/H'+report['title'])
        
        process_date = {}
        process_date['D'] = lambda x : reduce(lambda xx,yy : xx+'-'+yy,x.split('-')[1:3])
        process_date['M'] = lambda x : x.split('-')[1]
        process_date['Y'] = lambda x : x.split('-')[0]

        order_date = {}
        order_date['D'] = lambda x : time.mktime((2005,int(x.split('-')[0]), int(x.split('-')[1]),0,0,0,0,0,0))
        order_date['M'] = lambda x : x
        order_date['Y'] = lambda x : x

        ar = area.T(size=(350,350),
            x_axis = axis.X(label = fields[0]['name'], format="/a-30{}%s"),
            y_axis = axis.Y(label = ', '.join(map(lambda x : x['name'], fields[1:]))))

        idx = 0 
        date_idx = None
        fct = {}
        for f in fields:
            field_id = (f['field_child3'] and f['field_child3'][0]) or (f['field_child2'] and f['field_child2'][0]) or (f['field_child1'] and f['field_child1'][0]) or (f['field_child0'] and f['field_child0'][0])
            if field_id:
                type = pool.get('ir.model.fields').read(cr, uid, [field_id],['ttype'])
                if type[0]['ttype'] == 'date':
                    date_idx = idx
                    fct[idx] = process_date[report['frequency']] 
                else:
                    fct[idx] = lambda x : x
            else:
                fct[idx] = lambda x : x
            idx+=1
        
        # plot are usually displayed year by year
        # so we do so if the first field is a date
        data_by_year = {}
        if date_idx != None:
            for r in results:
                key = process_date['Y'](r[date_idx])
                if not data_by_year.has_key(key):
                    data_by_year[key] = []
                for i in range(len(r)):
                    r[i] = fct[i](r[i])
                data_by_year[key].append(r)
        else:
            data_by_year[''] = results


        nb_bar = len(data_by_year)*(len(fields)-1)
        colors = map(lambda x:fill_style.Plain(bgcolor=x), misc.choice_colors(nb_bar))
        
        abscissa = {}
        for line in data_by_year.keys():
            fields_bar = []
            # sum data and save it in a list. An item for a fields
            for d in data_by_year[line]:
                for idx in range(len(fields)-1):
                    fields_bar.append({})
                    if fields_bar[idx].has_key(d[0]):
                        fields_bar[idx][d[0]] += d[idx+1]
                    else:
                        fields_bar[idx][d[0]] = d[idx+1]
            for idx  in range(len(fields)-1):
                data = {}
                for k in fields_bar[idx].keys():
                    if data.has_key(k):
                        data[k] += fields_bar[idx][k]
                    else:
                        data[k] = fields_bar[idx][k]
                data_cum = []
                prev = 0.0
                keys = data.keys()
                keys.sort()
                # cumulate if necessary
                for k in keys:
                    data_cum.append([k, float(data[k])+float(prev)])
                    if fields[idx+1]['cumulate']:
                        prev += data[k]
                        
                idx0 = 0
                plot = bar_plot.T(label=fields[idx+1]['name']+' '+str(line), data = data_cum, cluster=(idx0*(len(fields)-1)+idx,nb_bar), fill_style=colors[idx0*(len(fields)-1)+idx])
                ar.add_plot(plot)
                abscissa.update(fields_bar[idx])
            idx0 += 1
        abscissa = map(lambda x : [x, None], abscissa)
        abscissa.sort()
        ar.x_coord = category_coord.T(abscissa,0)
        ar.draw(can)

        can.close()
        self.obj = external_pdf(pdf_string.getvalue())
        self.obj.render()
        pdf_string.close()
        return True

    def _create_pie(self, cr, uid, ids, report, fields, results, context):
        pdf_string = cStringIO.StringIO()
        can = canvas.init(fname=pdf_string, format='pdf')
        ar = area.T(size=(350,350), legend=legend.T(),
                    x_grid_style = None, y_grid_style = None)
        colors = map(lambda x:fill_style.Plain(bgcolor=x), misc.choice_colors(len(results)))

        if reduce(lambda x,y : x+y, map(lambda x : x[1],results)) == 0.0:
            raise except_osv(_('Error'), _("The sum of the data (2nd field) is null.\nWe can't draw a pie chart !"))

        plot = pie_plot.T(data=results, arc_offsets=[0,10,0,10],
                          shadow = (2, -2, fill_style.gray50),
                          label_offset = 25,
                          arrow_style = arrow.a3,
                          fill_styles=colors)
        ar.add_plot(plot)
        ar.draw(can)
        can.close()
        self.obj = external_pdf(pdf_string.getvalue())
        self.obj.render()
        pdf_string.close()
        return True

    def _create_table(self, uid, ids, report, fields, tree, results, context):
        pageSize=common.pageSize.get(report['print_format'], [210.0,297.0])
        if report['print_orientation']=='landscape':
            pageSize=[pageSize[1],pageSize[0]]

        new_doc = etree.Element('report')
        config = etree.SubElement(new_doc, 'config')

        def _append_node(name, text):
            n = etree.SubElement(config, name)
            n.text = text

        _append_node('date', time.strftime('%d/%m/%Y'))
        _append_node('PageSize', '%.2fmm,%.2fmm' % tuple(pageSize))
        _append_node('PageFormat', '%s' % report['print_format'])
        _append_node('PageWidth', '%.2f' % (pageSize[0] * 2.8346,))
        _append_node('PageHeight', '%.2f' %(pageSize[1] * 2.8346,))

        length = pageSize[0]-30-reduce(lambda x,y:x+(y['width'] or 0), fields, 0)
        count = 0
        for f in fields:
            if not f['width']: count+=1
        for f in fields:
            if not f['width']:
                f['width']=round((float(length)/count)-0.5)

        _append_node('tableSize', '%s' %  ','.join(map(lambda x: '%.2fmm' % (x['width'],), fields)))
        _append_node('report-header', '%s' % (report['title'],))
        _append_node('report-footer', '%s' % (report['footer'],))

        header = etree.SubElement(new_doc, 'header')
        for f in fields:
            field = etree.SubElement(header, 'field')
            field.text = f['name']

        lines = etree.SubElement(new_doc, 'lines')
        for line in results:
            node_line = etree.SubElement(lines, 'row')
            for f in range(len(fields)):
                col = etree.SubElement(node_line, 'col', tree='no')
                if line[f] != None:
                    col.text = line[f] or ''
                else:
                    col.text = '/'

        transform = etree.XSLT(
            etree.parse(os.path.join(tools.config['root_path'],
                                     'addons/base/report/custom_new.xsl')))
        rml = etree.tostring(transform(new_doc))

        self.obj = render.rml(rml)
        self.obj.render()
        return True
report_custom('report.custom')


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

