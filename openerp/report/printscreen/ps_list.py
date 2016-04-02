# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import openerp
from openerp.report.interface import report_int
import openerp.tools as tools
from openerp.tools.safe_eval import safe_eval as eval
from lxml  import etree
from openerp.report import render, report_sxw
import locale

import time, os
from operator import itemgetter
from datetime import datetime


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
        except Exception:
            dom = etree.XML(view)
        return self._parse_node(dom)

    def create(self, cr, uid, ids, datas, context=None):
        if not context:
            context={}
        self.cr=cr
        self.context = context
        self.groupby = context.get('group_by',[])
        self.groupby_no_leaf = context.get('group_by_no_leaf',False)
        registry = openerp.registry(cr.dbname)
        model = registry[datas['model']]
        model_id = registry['ir.model'].search(cr, uid, [('model','=',model._name)])
        model_desc = model._description
        if model_id:
            model_desc = registry['ir.model'].browse(cr, uid, model_id[0], context).name
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
        return self.obj.get(), 'pdf'


    def _create_table(self, uid, ids, fields, fields_order, results, context, title=''):
        pageSize=[297.0, 210.0]

        new_doc = etree.Element("report")
        config = etree.SubElement(new_doc, 'config')

        def _append_node(name, text):
            n = etree.SubElement(config, name)
            n.text = text

        #_append_node('date', time.strftime('%d/%m/%Y'))
        _append_node('date', time.strftime(str(locale.nl_langinfo(locale.D_FMT).replace('%y', '%Y'))))
        _append_node('PageSize', '%.2fmm,%.2fmm' % tuple(pageSize))
        _append_node('PageWidth', '%.2f' % (pageSize[0] * 2.8346,))
        _append_node('PageHeight', '%.2f' %(pageSize[1] * 2.8346,))
        _append_node('report-header', title)

        registry = openerp.registry(self.cr.dbname)
        _append_node('company', registry['res.users'].browse(self.cr,uid,uid).company_id.name)
        rpt_obj = registry['res.users']
        rml_obj=report_sxw.rml_parse(self.cr, uid, rpt_obj._name,context)
        _append_node('header-date', str(rml_obj.formatLang(time.strftime("%Y-%m-%d"),date=True))+' ' + str(time.strftime("%H:%M")))
        l = []
        t = 0
        strmax = (pageSize[0]-40) * 2.8346
        temp = []
        tsum = []
        for i in range(0, len(fields_order)):
            temp.append(0)
            tsum.append(0)
        ince = -1
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
                        format = str(locale.nl_langinfo(locale.D_FMT).replace('%y', '%Y'))
                        d1 = datetime.strptime(line[f],'%Y-%m-%d')
                        new_d1 = d1.strftime(format)
                    line[f] = new_d1

                if fields[f]['type'] == 'time' and line[f]:
                    new_d1 = line[f]
                    if not line.get('__group'):
                        format = str(locale.nl_langinfo(locale.T_FMT))
                        d1 = datetime.strptime(line[f], '%H:%M:%S')
                        new_d1 = d1.strftime(format)
                    line[f] = new_d1

                if fields[f]['type'] == 'datetime' and line[f]:
                    new_d1 = line[f]
                    if not line.get('__group'):
                        format = str(locale.nl_langinfo(locale.D_FMT).replace('%y', '%Y'))+' '+str(locale.nl_langinfo(locale.T_FMT))
                        d1 = datetime.strptime(line[f], '%Y-%m-%d %H:%M:%S')
                        new_d1 = d1.strftime(format)
                    line[f] = new_d1


                if line.get('__group'):
                    col = etree.SubElement(node_line, 'col', para='group', tree='no')
                else:
                    col = etree.SubElement(node_line, 'col', para='yes', tree='no')

                # Prevent empty labels in groups
                if f == line.get('__grouped_by') and line.get('__group') and not line[f] and not float_flag and not temp[count]:
                    col.text = line[f] = 'Undefined'
                    col.set('tree', 'undefined')

                if line[f] is not None:
                    col.text = tools.ustr(line[f] or '')
                    if float_flag:
                        col.set('tree','float')
                    if line.get('__no_leaf') and temp[count] == 1 and f != 'id' and not line['__context']['group_by']:
                        tsum[count] = float(tsum[count]) + float(line[f])
                    if not line.get('__group') and f != 'id' and temp[count] == 1:
                        tsum[count] = float(tsum[count])  + float(line[f])
                else:
                    col.text = '/'

        node_line = etree.SubElement(lines, 'row')
        for f in range(0, len(fields_order)):
            col = etree.SubElement(node_line, 'col', para='group', tree='no')
            col.set('tree', 'float')
            if tsum[f] is not None:
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
