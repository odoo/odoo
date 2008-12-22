# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2008 Tiny SPRL (<http://tiny.be>). All Rights Reserved
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

from report import render

from xml.dom import minidom
import libxml2
import libxslt

import time, os

class report_printscreen_list(report_int):
    def __init__(self, name):
        report_int.__init__(self, name)

    def _parse_node(self, root_node):
        result = []
        for node in root_node.childNodes:
            if node.localName == 'field':
                attrsa = node.attributes
                attrs = {}
                if not attrsa is None:
                    for i in range(attrsa.length):
                        attrs[attrsa.item(i).localName] = attrsa.item(i).nodeValue
                result.append(attrs['name'])
            else:
                result.extend(self._parse_node(node))
        return result

    def _parse_string(self, view):
        dom = minidom.parseString(unicode(view, 'utf-8').encode('utf-8'))
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
        rows = model.read(cr, uid, datas['ids'], result['fields'].keys(), context )
        res = self._create_table(uid, datas['ids'], result['fields'], fields_order, rows, context, model_desc)
        return (self.obj.get(), 'pdf')


    def _create_table(self, uid, ids, fields, fields_order, results, context, title=''):
        pageSize=[297.0, 210.0]

        impl = minidom.getDOMImplementation()
        new_doc = impl.createDocument(None, "report", None)

        # build header
        config = new_doc.createElement("config")

        def _append_node(name, text):
            n = new_doc.createElement(name)
            t = new_doc.createTextNode(text)
            n.appendChild(t)
            config.appendChild(n)

        _append_node('date', time.strftime('%d/%m/%Y'))
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
            if fields[f]['type'] in ('date','time','float','integer'):
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
        new_doc.childNodes[0].appendChild(config)
        header = new_doc.createElement("header")


        for f in fields_order:
            field = new_doc.createElement("field")
            field_txt = new_doc.createTextNode(fields[f]['string'] or '')
            field.appendChild(field_txt)
            header.appendChild(field)

        new_doc.childNodes[0].appendChild(header)

        lines = new_doc.createElement("lines")

        tsum = []
        count = len(fields_order)
        for i in range(0,count):
            tsum.append(0)


        for line in results:
            node_line = new_doc.createElement("row")
            count = -1
            for f in fields_order:

                count += 1

                if fields[f]['type']=='many2one' and line[f]:
                    line[f]= line[f][1]

                if fields[f]['type'] in ('one2many','many2many') and line[f]:
                    line[f] = '( '+str(len(line[f])) + ' )'
                if fields[f]['type'] == 'float':
                    precision=(('digits' in fields[f]) and fields[f]['digits'][1]) or 2
                    line[f]='%.2f'%(line[f])

                col = new_doc.createElement("col")
                col.setAttribute('para','yes')
                col.setAttribute('tree','no')
                if line[f] != None:
                    txt = new_doc.createTextNode(str(line[f] or ''))
                    if temp[count] == 1:
                        tsum[count] = float(tsum[count])  + float(line[f]);

                else:
                    txt = new_doc.createTextNode('/')
                col.appendChild(txt)
                node_line.appendChild(col)
            lines.appendChild(node_line)
        node_line = new_doc.createElement("row")
        lines.appendChild(node_line)
        node_line = new_doc.createElement("row")
        for f in range(0,count+1):
            col = new_doc.createElement("col")
            col.setAttribute('para','yes')
            col.setAttribute('tree','no')
            if tsum[f] != None:
               if tsum[f] >= 0.01 :
                  total = '%.2f'%(tsum[f])
                  txt = new_doc.createTextNode(str(total or ''))
               else :
                   txt = new_doc.createTextNode(str(tsum[f] or ''))
            else:
                txt = new_doc.createTextNode('/')
            if f == 0:
                txt = new_doc.createTextNode('Total')

            col.appendChild(txt)
            node_line.appendChild(col)

        lines.appendChild(node_line)


        new_doc.childNodes[0].appendChild(lines)

        styledoc = libxml2.parseFile(os.path.join(tools.config['root_path'],'addons/base/report/custom_new.xsl'))
        style = libxslt.parseStylesheetDoc(styledoc)
        doc = libxml2.parseDoc(new_doc.toxml(encoding='utf-8'))
        rml_obj = style.applyStylesheet(doc, None)
        rml = style.saveResultToString(rml_obj)
        self.obj = render.rml(rml, title=self.title)
        self.obj.render()
        return True
report_printscreen_list('report.printscreen.list')


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
