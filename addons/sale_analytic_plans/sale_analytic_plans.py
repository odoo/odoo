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

from openerp.osv import fields, osv
from openerp.tools.translate import _
import openerp.tools

class sale_order_line(osv.osv):
    _inherit = 'sale.order.line'
    _columns = {
        'analytics_id': fields.many2one('account.analytic.plan.instance', 'Analytic Distribution'),
    }
    def invoice_line_create(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        line_obj = self.pool.get('account.invoice.line')
        create_ids = super(sale_order_line, self).invoice_line_create(cr, uid, ids, context=context)
        i = 0
        for line in self.browse(cr, uid, ids, context=context):
            line_obj.write(cr, uid, [create_ids[i]], {'analytics_id': line.analytics_id.id})
            i = i + 1
        return create_ids


class sale_order(osv.Model):
    _inherit = "sale.order"

    def _get_analytic_account(self, cr, uid, order):
        cr.execute('SELECT DISTINCT acc.id, acc.complete_name '
                   'FROM account_analytic_account as acc '
                   'INNER JOIN account_analytic_plan_instance_line as plan_line on (acc.id = plan_line.analytic_account_id) '
                   'INNER JOIN account_analytic_plan_instance as plan on (plan_line.plan_id = plan.id) '
                   'INNER JOIN sale_order_line as sale_line on (plan.id = sale_line.analytics_id AND sale_line.order_id = %s) '
                   'WHERE acc.state in %s', ((tuple([order.id])), ('close', 'cancelled', 'pending')))
        contract_list = [(rec[0], rec[1]) for rec in cr.fetchall()]
        return contract_list

    def _check_order_before_confirm(self, cr, uid, order, context=None):
        contract_list = self._get_analytic_account(cr, uid, order)
        models_data = self.pool['ir.model.data']
        if contract_list:
            button_string = ''
            contract_ids, contract_name = zip(*contract_list)
            model, action_id = models_data.get_object_reference(cr, uid, 'analytic', 'action_account_analytic_account_form')
            action = self.pool.get('ir.actions.act_window').read(cr, uid, action_id, ['name', 'type', 'view_type', 'view_mode', 'res_model', 'views', 'view', 'domain'])
            action['name'] = _('Contract')
            action['domain'] = [('id', 'in', contract_ids)]
            if len(contract_ids) == 1:
                form_view = models_data.get_object_reference(cr, uid, 'analytic', 'view_account_analytic_account_form')[1]
                action['views'] = [(form_view or False, 'form'), (False, 'list')]
                action['res_id'] = contract_ids[0]
                button_string = _('Modify Contract')
            else:
                tree_view = models_data.get_object_reference(cr, uid, 'analytic', 'view_account_analytic_account_tree')[1]
                action['views'] = [(tree_view or False, 'list'), (False, 'form')]
                button_string = _('Modify Contract(s)')
            msg = _('''Contract(s) mentioned below %s in "Closed/Cancelled/To Renew" state, please renew %s before confirmation :\n%s.''') % (len(contract_list) > 1 and 'are' or 'is', len(contract_name) > 1 and 'them' or 'it', '-' + '\n- '.join(contract_name))
            raise openerp.exceptions.RedirectWarning(msg, action, button_string)
        return super(sale_order, self)._check_order_before_confirm(cr, uid, order, context=context)

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
