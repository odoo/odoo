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

from report.interface import report_int
import pooler
import tools
from tools.safe_eval import safe_eval as eval
from lxml  import etree
from report import render

import time, os
from operator import itemgetter
from datetime import datetime
from report import report_sxw

class report_printscreen_list(report_int):
    def __init__(self, name):
        report_int.__init__(self, name)
        self.context = {}
        self.groupby = []
        self.cr=''

    def _parse_node(self, root_node):
        result = []
        for node in root_node:
            field_name = node.get('name')
            if not eval(str(node.attrib.get('invisible',False)),{'context':self.context}):
                if node.tag == 'field':
                    if field_name in self.groupby:
                        continue
                    result.append(field_name)
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
        self.cr=cr
        self.context = context
        self.groupby = context.get('group_by',[])
        self.groupby_no_leaf = context.get('group_by_no_leaf',False)
        pool = pooler.get_pool(cr.dbname)
        lang_obj = pool.get('res.lang')
        lang_id = lang_obj.search(cr, uid, [('code','=',context.get('lang') or 'en_US')], context=context)
        lang = lang_obj.browse(cr, uid, lang_id[0], context=context)
        self.d_fmt = lang.date_format
        self.t_fmt = lang.time_format
        self.d_t_fmt = self.d_fmt + ' ' + self.t_fmt
        model = pool.get(datas['model'])
        model_id = pool.get('ir.model').search(cr, uid, [('model','=',model._name)])
        model_desc = model._description
        if model_id:
            model_desc = pool.get('ir.model').browse(cr, uid, model_id[0], context).name
        self.title = model_desc
        datas['ids'] = ids
        result = model.fields_view_get(cr, uid, view_type='tree', context=context)
        fields_order =  self.groupby + self._parse_string(result['arch'])
        if self.groupby:
            rows = []
            def get_groupby_data(groupby = [], domain = []):
                records =  model.read_group(cr, uid, domain, fields_order, groupby , 0, None, context)
                for rec in records:
                    rec['__group'] = True
                    rec['__no_leaf'] = self.groupby_no_leaf
                    rec['__grouped_by'] = groupby[0] if (isinstance(groupby, list) and groupby) else groupby
                    for f in fields_order:
                        if f not in rec:
                            rec.update({f:False})
                        elif isinstance(rec[f], tuple):
                            rec[f] = rec[f][1]
                    rows.append(rec)
                    inner_groupby = (rec.get('__context', {})).get('group_by',[])
                    inner_domain = rec.get('__domain', [])
                    if inner_groupby:
                        get_groupby_data(inner_groupby, inner_domain)
                    else:
                        if self.groupby_no_leaf:
                            continue
                        child_ids = model.search(cr, uid, inner_domain)
                        res = model.read(cr, uid, child_ids, result['fields'].keys(), context)
                        res.sort(lambda x,y: cmp(ids.index(x['id']), ids.index(y['id'])))
                        rows.extend(res)
            dom = [('id','in',ids)]
            if self.groupby_no_leaf and len(ids) and not ids[0]:
                dom = datas.get('_domain',[])
            get_groupby_data(self.groupby, dom)
        else:
            rows = model.read(cr, uid, datas['ids'], result['fields'].keys(), context)
            ids2 = map(itemgetter('id'), rows) # getting the ids from read result
            if datas['ids'] != ids2: # sorted ids were not taken into consideration for print screen
                rows_new = []
                for id in datas['ids']:
                    rows_new += [elem for elem in rows if elem['id'] == id]
                rows = rows_new
        res = self._create_table(uid, datas['ids'], result['fields'], fields_order, rows, context, model_desc)
        return (self.obj.get(), 'pdf')


    def _create_table(self, uid, ids, fields, fields_order, results, context, title=''):
        pageSize=[297.0, 210.0]

        new_doc = etree.Element("report")
        config = etree.SubElement(new_doc, 'config')

        def _append_node(name, text):
            n = etree.SubElement(config, name)
            n.text = text

        #_append_node('date', time.strftime('%d/%m/%Y'))
        _append_node('date', time.strftime(self.d_fmt))
        _append_node('PageSize', '%.2fmm,%.2fmm' % tuple(pageSize))
        _append_node('PageWidth', '%.2f' % (pageSize[0] * 2.8346,))
        _append_node('PageHeight', '%.2f' %(pageSize[1] * 2.8346,))
        _append_node('report-header', title)

        _append_node('company', pooler.get_pool(self.cr.dbname).get('res.users').browse(self.cr,uid,uid).company_id.name)
        rpt_obj = pooler.get_pool(self.cr.dbname).get('res.users')
        rml_obj=report_sxw.rml_parse(self.cr, uid, rpt_obj._name,context)
        _append_node('header-date', datetime.now().strftime(self.d_t_fmt))
        l = []
        t = 0
        strmax = (pageSize[0]-40) * 2.8346
        temp = []
        tsum = []
        for i in range(0, len(fields_order)):
            temp.append(0)
            tsum.append(0)
        ince = -1;
        for f in fields_order:
            s = 0
            ince += 1
            if fields[f]['type'] in ('date','time','datetime','float','integer'):
                s = 60
                strmax -= s
                if fields[f]['type'] in ('float','integer'):
                    temp[ince] = 1
            else:
                t += fields[f].get('size', 80) / 28 + 1

            l.append(s)
        for pos in range(len(l)):
            if not l[pos]:
                s = fields[fields_order[pos]].get('size', 80) / 28 + 1
                l[pos] = strmax * s / t

        _append_node('tableSize', ','.join(map(str,l)) )

        header = etree.SubElement(new_doc, 'header')
        for f in fields_order:
            field = etree.SubElement(header, 'field')
            field.text = tools.ustr(fields[f]['string'] or '')

        lines = etree.SubElement(new_doc, 'lines')
        for line in results:
            node_line = etree.SubElement(lines, 'row')
            count = -1
            for f in fields_order:
                float_flag = 0
                count += 1
                if fields[f]['type']=='many2one' and line[f]:
                    if not line.get('__group'):
                        line[f] = line[f][1]
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
                    new_d1 = line[f]
                    if not line.get('__group'):
                        d1 = datetime.strptime(line[f], tools.DEFAULT_SERVER_DATE_FORMAT)
                        new_d1 = d1.strftime(self.d_fmt)
                    line[f] = new_d1

                if fields[f]['type'] == 'time' and line[f]:
                    new_d1 = line[f]
                    if not line.get('__group'):
                        d1 = datetime.strptime(line[f], tools.DEFAULT_SERVER_TIME_FORMAT)
                        new_d1 = d1.strftime(self.t_fmt)
                    line[f] = new_d1

                if fields[f]['type'] == 'datetime' and line[f]:
                    new_d1 = line[f]
                    if not line.get('__group'):
                        d1 = datetime.strptime(line[f][:19], tools.DEFAULT_SERVER_DATETIME_FORMAT)
                        new_d1 = d1.strftime(self.d_t_fmt)
                    line[f] = new_d1


                if line.get('__group'):
                    col = etree.SubElement(node_line, 'col', para='group', tree='no')
                else:
                    col = etree.SubElement(node_line, 'col', para='yes', tree='no')

                # Prevent empty labels in groups
                if f == line.get('__grouped_by') and line.get('__group') and not line[f] and not float_flag and not temp[count]:
                    col.text = line[f] = 'Undefined'
                    col.set('tree', 'undefined')

                if line[f] != None:
                    col.text = tools.ustr(line[f] or '')
                    if float_flag:
                        col.set('tree','float')
                    if line.get('__no_leaf') and temp[count] == 1 and f != 'id' and not line['__context']['group_by']:
                        tsum[count] = float(tsum[count]) + float(line[f])
                    if not line.get('__group') and f != 'id' and temp[count] == 1:
                        tsum[count] = float(tsum[count])  + float(line[f]);
                else:
                    col.text = '/'

        node_line = etree.SubElement(lines, 'row')
        for f in range(0, len(fields_order)):
            col = etree.SubElement(node_line, 'col', para='group', tree='no')
            col.set('tree', 'float')
            if tsum[f] != None:
                if tsum[f] != 0.0:
                    digits = fields[fields_order[f]].get('digits', (16, 2))
                    prec = '%%.%sf' % (digits[1], )
                    total = prec % (tsum[f], )
                    txt = str(total or '')
                else:
                    txt = str(tsum[f] or '')
            else:
                txt = '/'
            if f == 0:
                txt ='Total'
                col.set('tree','no')
            col.text = tools.ustr(txt or '')

        transform = etree.XSLT(
            etree.parse(os.path.join(tools.config['root_path'],
                                     'addons/base/report/custom_new.xsl')))
        rml = etree.tostring(transform(new_doc))
        self.obj = render.rml(rml, title=self.title)
        self.obj.render()
        return True
report_printscreen_list('report.printscreen.list')


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
