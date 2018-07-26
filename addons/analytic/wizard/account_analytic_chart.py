# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from openerp.osv import fields, osv
from openerp.tools.safe_eval import safe_eval

class account_analytic_chart(osv.osv_memory):
    _name = 'account.analytic.chart'
    _description = 'Account Analytic Chart'

    _columns = {
        'from_date': fields.date('From'),
        'to_date': fields.date('To'),
    }

    def analytic_account_chart_open_window(self, cr, uid, ids, context=None):
        mod_obj = self.pool.get('ir.model.data')
        act_obj = self.pool.get('ir.actions.act_window')
        if context is None:
            context = {}
        result = mod_obj.get_object_reference(cr, uid, 'analytic', 'action_analytic_account_form')
        id = result and result[1] or False
        result = act_obj.read(cr, uid, [id], context=context)[0]
        result_context = safe_eval(result.get('context', '{}'))
        data = self.read(cr, uid, ids, [])[0]
        if data['from_date']:
            result_context.update({'from_date': data['from_date']})
        if data['to_date']:
            result_context.update({'to_date': data['to_date']})
        result['context'] = str(result_context)
        return result
