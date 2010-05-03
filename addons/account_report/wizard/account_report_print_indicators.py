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
from lxml import etree

from osv import fields, osv
from tools.translate import _

class account_report_print_indicators(osv.osv_memory):
    """
    This wizard will print indicators
    """
    _name = "account.report.print.indicators"
    _description = "Print Indicators"
    _columns = {
        'select_base': fields.selection([('year','Based On Fiscal Years'),
                                         ('periods','Based on Fiscal Periods')],'Choose Criteria',required=True),
        'base_selection': fields.many2many('account.fiscalyear', 'indicator_rel','account_id','fiscalyear_id','Fiscal year'),
        }
    _defaults ={
        'select_base':'year'
        }

    def next(self, cr, uid, ids, context=None):
        obj_model = self.pool.get('ir.model.data')
        if context is None:
            context = {}
        data = self.read(cr, uid, ids, [])[0]
        context.update({'base': data['select_base']})
        model_data_ids = obj_model.search(cr,uid,[('model','=','ir.ui.view'),('name','=','account_report_print_indicators_relation_view')])
        resource_id = obj_model.read(cr, uid, model_data_ids, fields=['res_id'])[0]['res_id']
        return {
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'account.report.print.indicators',
            'views': [(resource_id,'form')],
            'type': 'ir.actions.act_window',
            'target': 'new',
            'context': context,
        }

    def fields_view_get(self, cr, uid, view_id=None, view_type='form', context=None, toolbar=False, submenu=False):
        record_id = context and context.get('base', False) or False
        res = super(account_report_print_indicators, self).fields_view_get(cr, uid, view_id=view_id, view_type=view_type, context=context, toolbar=toolbar,submenu=False)
        fields = res.get('fields',{})
        if record_id:
            if record_id == 'periods':
                fields.update({'base_selection': {'domain': [],'string': 'Periods','relation': 'account.period','context': '', 'selectable': True,'type':'many2many'}})
            view_obj = etree.XML(res['arch'])
            child = view_obj.getchildren()[0]
            field = etree.Element('field', attrib={'name':'base_selection'})
            child.addprevious(field)
            res['arch'] = etree.tostring(view_obj)
        return res

    def check_report(self, cr, uid, ids, context=None):
        datas = {}
        if context is None:
            context = {}
        data = self.read(cr, uid, ids, [])[0]
        data['select_base']=context['base']
        if len(data['base_selection'])>8:
            raise osv.except_osv(_('User Error!'),_("Please select maximum 8 records to fit the page-width."))
        datas = {
             'ids': context.get('active_ids', []),
             'model': 'ir.ui.menu',
             'form': data
            }
        return {
            'type': 'ir.actions.report.xml',
            'report_name': 'print.indicators',
            'datas': datas,
            }

account_report_print_indicators()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
