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

from report.interface import report_int
import pooler
import tools
from lxml  import etree
from report import render
import libxml2
import libxslt
import locale

import time, os
import mx.DateTime

class report_printscreen_list(report_int):
    def __init__(self, name):
        report_int.__init__(self, name)

    def _parse_node(self, root_node):
        result = []
        for node in root_node.getchildren():
            if node.tag == 'field':
                attrsa = node.attrib
                attrs = {}
                if not attrsa is None:
                   for key,val in attrsa.items():
                    attrs[key] = val
                result.append(attrs['name'])
            else:
                result.extend(self._parse_node(node))
        return result

    def _parse_string(self, view):
        try:
            dom = etree.XML(view.encode('utf-8'))
        except:
            dom = etree.XML(view)   
        return self._parse_node(dom)

    def create(self, cr, uid, ids, datas, context=None):
        if not context:
            context={}
        pool = pooler.get_pool(cr.dbname)
        model = pool.get(datas['model'])
        model_id = pool.get('ir.model').search(cr, uid, [('model','=',model._name)])
        if model_id:
            model_desc = pool.get('ir.model').browse(cr, uid, model_id[0], context).name
            self.title = model_desc
        else:
            model_desc = model._description
            self.title = model_desc

        datas['ids'] = ids
        model = pooler.get_pool(cr.dbname).get(datas['model'])

        result = model.fields_view_get(cr, uid, view_type='tree', context=context)
        fields_order = self._parse_string(result['arch'])
        rows = model.read(cr, uid, datas['ids'], result['fields'].keys(), context)
        ids2 = [x['id'] for x in rows] # getting the ids from read result
        
        if datas['ids'] != ids2: # sorted ids were not taken into consideration for print screen
            rows_new = []
            for id in datas['ids']:
                element = [elem for elem in rows if elem['id']==id]
                rows_new.append(element[0])
            rows = rows_new
        
        res = self._create_table(uid, datas['ids'], result['fields'], fields_order, rows, context, model_desc)
        return (self.obj.get(), 'pdf')


    def _create_table(self, uid, ids, fields, fields_order, results, context, title=''):
        pageSize=[297.0, 210.0]
        new_doc = etree.Element("report")
        config = etree.Element("config")

        # build header

        def _append_node(name, text):
            n = etree.Element(name)
            n.text = text
            config.append(n)

        #_append_node('date', time.strftime('%d/%m/%Y'))
        _append_node('date', time.strftime(str(locale.nl_langinfo(locale.D_FMT).replace('%y', '%Y'))))
        _append_node('PageSize', '%.2fmm,%.2fmm' % tuple(pageSize))
        _append_node('PageWidth', '%.2f' % (pageSize[0] * 2.8346,))
        _append_node('PageHeight', '%.2f' %(pageSize[1] * 2.8346,))

        _append_node('report-header', title)
        l = []
        t = 0
        rowcount=0;
        strmax = (pageSize[0]-40) * 2.8346
        temp = []
        count = len(fields_order)
        for i in range(0,count):
            temp.append(0)

        ince = -1;
        for f in fields_order:
            s = 0
            ince += 1
            if fields[f]['type'] in ('date','time','datetime','float','integer'):
                s = 60
                strmax -= s
                if fields[f]['type'] in ('float','integer'):
                    temp[ince]=1;
            else:
                t += fields[f].get('size', 80) / 28 + 1

            l.append(s)
        for pos in range(len(l)):
            if not l[pos]:
                s = fields[fields_order[pos]].get('size', 80) / 28 + 1
                l[pos] = strmax * s / t

        _append_node('tableSize', ','.join(map(str,l)) )
        new_doc.append(config)
        header=etree.Element("header")


        for f in fields_order:
            field = etree.Element("field")
            field.text = tools.ustr(fields[f]['string'] or '')
            header.append(field)

        new_doc.append(header)
        lines = etree.Element("lines")
        tsum = []
        count = len(fields_order)
        for i in range(0,count):
            tsum.append(0)
            
        for line in results:
            node_line = etree.Element("row")
            count = -1
            for f in fields_order:
                float_flag = 0
                count += 1

                if fields[f]['type']=='many2one' and line[f]:
                    line[f]= line[f][1]

                if fields[f]['type']=='selection' and line[f]:
                    for key, value in fields[f]['selection']:
                        if key == line[f]:
                            line[f] = value
                            break

                if fields[f]['type'] in ('one2many','many2many') and line[f]:
                    line[f] = '( '+tools.ustr(len(line[f])) + ' )'

                if fields[f]['type'] == 'float' and line[f]:
                    precision=(('digits' in fields[f]) and fields[f]['digits'][1]) or 2
                    prec ='%.' + str(precision) +'f'
                    line[f]=prec%(line[f])
                    float_flag = 1

                if fields[f]['type'] == 'date' and line[f]:
                    format = str(locale.nl_langinfo(locale.D_FMT).replace('%y', '%Y'))
                    d1= mx.DateTime.strptime(line[f],'%Y-%m-%d')
                    new_d1 = d1.strftime(format)
                    line[f] = new_d1
                    
                if fields[f]['type'] == 'time' and line[f]:
                    format = str(locale.nl_langinfo(locale.T_FMT))
                    d1= mx.DateTime.strptime(line[f],'%H:%M:%S')
                    new_d1 = d1.strftime(format)
                    line[f] = new_d1
                    
                if fields[f]['type'] == 'datetime' and line[f]:
                    format = str(locale.nl_langinfo(locale.D_FMT).replace('%y', '%Y'))+' '+str(locale.nl_langinfo(locale.T_FMT))
                    d1= mx.DateTime.strptime(line[f],'%Y-%m-%d %H:%M:%S')
                    new_d1 = d1.strftime(format)
                    line[f] = new_d1
                    
                col = etree.Element("col")
                col.set('para','yes')
                col.set('tree','no')
                if line[f] != None:
                    col.text = tools.ustr(line[f] or '')
                    if float_flag:
                       col.set('tree','float') 
                    if temp[count] == 1:
                        tsum[count] = float(tsum[count])  + float(line[f]);
                        
                        
                else:
                     col.text = '/'
                node_line.append(col)
            lines.append(node_line)
        node_line = etree.Element("row")
        lines.append(node_line)

        for f in range(0,count+1):
            col = etree.Element("col")
            col.set('para','yes')
            col.set('tree','no')
            if tsum[f] != None:
               if tsum[f] >= 0.01 :
                   prec = '%.' +  str(tools.config['price_accuracy'])  + 'f'
                   total = prec%(tsum[f])
                   txt = str(total or '')
                   col.set('tree','float')
               else:
                   txt = str(tsum[f] or '')
            else:
                txt = '/'
            if f == 0:
                txt ='Total'

            col.text = tools.ustr(txt or '')
            node_line.append(col)

        lines.append(node_line)

        new_doc.append(lines)
        styledoc = libxml2.parseFile(os.path.join(tools.config['root_path'],'addons/base/report/custom_new.xsl'))
        style = libxslt.parseStylesheetDoc(styledoc)
        doc = libxml2.parseDoc(etree.tostring(new_doc))
        rml_obj = style.applyStylesheet(doc, None)
        rml = style.saveResultToString(rml_obj)
        self.obj = render.rml(rml, title=self.title)
        self.obj.render()
        return True
report_printscreen_list('report.printscreen.list')


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
