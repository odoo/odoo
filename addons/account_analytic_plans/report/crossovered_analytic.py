# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
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

import time
from openerp.osv import osv
from openerp.report import report_sxw


class crossovered_analytic(report_sxw.rml_parse):
    def __init__(self, cr, uid, name, context):
        super(crossovered_analytic, self).__init__(cr, uid, name, context = context)
        self.localcontext.update( {
            'time': time,
            'lines': self._lines,
            'ref_lines': self._ref_lines,
            'find_children': self.find_children,
        })
        self.base_amount = 0.00

    def find_children(self, ref_ids):
        if not ref_ids: return []
        to_return_ids = []
        final_list = []
        parent_list = []
        set_list = []
        analytic_obj = self.pool.get('account.analytic.account')
        for id in ref_ids:
            # to avoid duplicate entries
            if id not in to_return_ids:
                to_return_ids.append(analytic_obj.search(self.cr,self.uid,[('parent_id','child_of',[id])]))
        data_accnt = analytic_obj.browse(self.cr,self.uid,to_return_ids[0])
        for data in data_accnt:
            if data.parent_id and data.parent_id.id == ref_ids[0]:
                parent_list.append(data.id)
        final_list.append(ref_ids[0])
        set_list = self.set_account(parent_list)
        final_list.extend(set_list)
        return final_list #to_return_ids[0]

    def set_account(self, cats):
        lst = []
        category = self.pool.get('account.analytic.account').read(self.cr, self.uid, cats)
        for cat in category:
            lst.append(cat['id'])
            if cat['child_ids']:
                lst.extend(self.set_account(cat['child_ids']))
        return lst

    def _ref_lines(self, form):
        result = []
        res = {}
        acc_pool = self.pool.get('account.analytic.account')
        line_pool = self.pool.get('account.analytic.line')

        self.dict_acc_ref = {}
        filters = [
            'date >= %(date1)s',
            'date <= %(date2)s',
        ]
        params = {
            'date1': form['date1'],
            'date2': form['date2']
        }
        if form['journal_ids']:
            filters.append('journal_id IN %(journal_ids)s')
            params['journal_ids'] = tuple(form['journal_ids'])
        else:
            filters.append('journal_id IS NOT NULL')

        self.cr.execute(
            "SELECT id FROM account_analytic_line WHERE " + ' AND '.join(filters),
            params
        )

        l_ids = self.cr.fetchall()
        line_ids = [x[0] for x in l_ids]

        obj_line = line_pool.browse(self.cr,self.uid,line_ids)

        #this structure will be usefull for easily knowing the account_analytic_line that are related to the reference account. At this purpose, we save the move_id of analytic lines.
        self.dict_acc_ref[form['ref']] = []
        children_list = acc_pool.search(self.cr, self.uid, [('parent_id', 'child_of', [form['ref']])])
        for obj in obj_line:
            if obj.account_id.id in children_list:
                if obj.move_id and obj.move_id.id not in self.dict_acc_ref[form['ref']]:
                    self.dict_acc_ref[form['ref']].append(obj.move_id.id)

        res['ref_name'] = acc_pool.name_get(self.cr, self.uid, [form['ref']])[0][1]
        res['ref_code'] = acc_pool.browse(self.cr, self.uid, form['ref']).code

        self.final_list = children_list
        selected_ids = line_pool.search(self.cr, self.uid, [('account_id', 'in' ,self.final_list)])
        
        res['ref_qty'] = 0.0
        res['ref_amt'] = 0.0
        self.base_amount = 0.0
        
        if selected_ids:
            params['selected_ids'] = tuple(selected_ids)
            filters = [
                'aal.account_id = aaa.id',
                'aal.id IN %(selected_ids)s',
                'aal.date >= %(date1)s',
                'aal.date <= %(date2)s',
            ]
            if form['journal_ids']:
                filters.append('aal.journal_id in %(journal_ids)s')
            else:
                filters.append('aal.journal_id IS NOT NULL')

            self.cr.execute(
                "SELECT SUM(aal.amount) AS amt, SUM(aal.unit_amount) AS qty"
                " FROM account_analytic_line AS aal, account_analytic_account AS aaa"
                " WHERE " + ' AND '.join(filters),
                params
            )
            info=self.cr.dictfetchall()
            res['ref_qty'] = info[0]['qty']
            res['ref_amt'] = info[0]['amt']
            self.base_amount = info[0]['amt']
        result.append(res)
        return result

    def _lines(self, form, ids=None):
        if ids is None:
            ids = {}
        if not ids:
            ids = self.ids

        filters = [
            'aal.account_id = aaa.id',
            'aal.date >= %(date1)s',
            'aal.date <= %(date2)s',
        ]
        params = {
            'date1': form['date1'],
            'date2': form['date2'],
        }
        if form['journal_ids']:
            filters.append('aal.journal_id IN %(journal_ids)s')
            params['journal_ids'] = tuple(form['journal_ids'])
        else:
            filters.append('aal.journal_id IS NOT NULL')

        acc_pool = self.pool.get('account.analytic.account')
        line_pool = self.pool.get('account.analytic.line')
        acc_id = []
        final = []
        self.list_ids = []

        self.final_list = self.find_children(ids)

        for acc_id in self.final_list:
            selected_ids = line_pool.search(self.cr, self.uid, [('account_id','=',acc_id), ('move_id', 'in', self.dict_acc_ref[form['ref']])])
            if selected_ids:
                filters.append('aal.id IN %(selected_ids)s')
                params['selected_ids'] = tuple(selected_ids)

                self.cr.execute(
                    "SELECT aaa.code AS code, SUM(aal.amount) AS amt, SUM(aal.unit_amount) AS qty, aaa.name AS acc_name, aal.account_id AS id"
                    " FROM account_analytic_line AS aal, account_analytic_account AS aaa"
                    " WHERE " + ' AND '.join(filters)
                    + " GROUP BY aal.account_id,aaa.name,aaa.code ORDER BY aal.account_id"
                )
                res = self.cr.dictfetchall()
                if res:
                    for element in res:
                        if self.base_amount <> 0.00:
                            element['perc'] = (element['amt'] / self.base_amount) * 100.00
                        else:
                            element['perc'] = 0.00
                else:
                    result = {}
                    res = []
                    result['id'] = acc_id
                    data_account = acc_pool.browse(self.cr, self.uid, acc_id)
                    result['acc_name'] = data_account.name
                    result['code'] = data_account.code
                    result['amt'] = result['qty'] = result['perc'] = 0.00
                    if not form['empty_line']:
                        res.append(result)
            else:
                result = {}
                res = []
                result['id'] = acc_id
                data_account = acc_pool.browse(self.cr, self.uid, acc_id)
                result['acc_name'] = data_account.name
                result['code'] = data_account.code
                result['amt'] = result['qty'] = result['perc'] = 0.00
                if not form['empty_line']:
                    res.append(result)

            for item in res:
                obj_acc = acc_pool.name_get(self.cr,self.uid,[item['id']])
                item['acc_name'] = obj_acc[0][1]
                final.append(item)
        return final


class report_crossoveredanalyticplans(osv.AbstractModel):
    _name = 'report.account_analytic_plans.report_crossoveredanalyticplans'
    _inherit = 'report.abstract_report'
    _template = 'account_analytic_plans.report_crossoveredanalyticplans'
    _wrapped_report_class = crossovered_analytic

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
