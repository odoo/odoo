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

import openerp
from openerp.report.interface import report_int
import openerp.tools as tools

from openerp.report import render
from lxml import etree

import time, os


class report_printscreen_list(report_int):
    def __init__(self, name):
        report_int.__init__(self, name)

    def _parse_node(self, root_node):
        result = []
        for node in root_node:
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
        dom = etree.XML(view)
        return self._parse_node(dom)

    def create(self, cr, uid, ids, datas, context=None):
        if not context:
            context={}
        datas['ids'] = ids
        registry = openerp.registry(cr.dbname)
        model = registry[datas['model']]
        # title come from description of model which are specified in py file.
        self.title = model._description
        result = model.fields_view_get(cr, uid, view_type='form', context=context)

        fields_order = self._parse_string(result['arch'])
        rows = model.read(cr, uid, datas['ids'], result['fields'].keys() )
        self._create_table(uid, datas['ids'], result['fields'], fields_order, rows, context, model._description)
        return self.obj.get(), 'pdf'


    def _create_table(self, uid, ids, fields, fields_order, results, context, title=''):
        pageSize=[297.0,210.0]

        new_doc = etree.Element("report")
        config = etree.SubElement(new_doc, 'config')

        # build header
        def _append_node(name, text):
            n = etree.SubElement(config, name)
            n.text = text

        _append_node('date', time.strftime('%d/%m/%Y'))
        _append_node('PageSize', '%.2fmm,%.2fmm' % tuple(pageSize))
        _append_node('PageWidth', '%.2f' % (pageSize[0] * 2.8346,))
        _append_node('PageHeight', '%.2f' %(pageSize[1] * 2.8346,))
        _append_node('report-header', title)

        l = []
        t = 0
        strmax = (pageSize[0]-40) * 2.8346
        for f in fields_order:
            s = 0
            if fields[f]['type'] in ('date','time','float','integer'):
                s = 60
                strmax -= s
            else:
                t += fields[f].get('size', 56) / 28 + 1
            l.append(s)
        for pos in range(len(l)):
            if not l[pos]:
                s = fields[fields_order[pos]].get('size', 56) / 28 + 1
                l[pos] = strmax * s / t
        _append_node('tableSize', ','.join(map(str,l)) )

        header = etree.SubElement(new_doc, 'header')
        for f in fields_order:
            field = etree.SubElement(header, 'field')
            field.text = fields[f]['string'] or ''

        lines = etree.SubElement(new_doc, 'lines')
        for line in results:
            node_line = etree.SubElement(lines, 'row')
            for f in fields_order:
                if fields[f]['type']=='many2one' and line[f]:
                    line[f] = line[f][1]
                if fields[f]['type'] in ('one2many','many2many') and line[f]:
                    line[f] = '( '+str(len(line[f])) + ' )'
                if fields[f]['type'] == 'float':
                    precision=(('digits' in fields[f]) and fields[f]['digits'][1]) or 2
                    line[f]=round(line[f],precision)
                col = etree.SubElement(node_line, 'col', tree='no')
                if line[f] is not None:
                    col.text = tools.ustr(line[f] or '')
                else:
                    col.text = '/'

        transform = etree.XSLT(
            etree.parse(os.path.join(tools.config['root_path'],
                                     'addons/base/report/custom_new.xsl')))
        rml = etree.tostring(transform(new_doc))

        self.obj = render.rml(rml, self.title)
        self.obj.render()
        return True
report_printscreen_list('report.printscreen.form')


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

