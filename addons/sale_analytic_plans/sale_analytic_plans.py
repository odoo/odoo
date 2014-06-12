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

class sale_order(osv.osv):
    _inherit = "sale.order"
    
    def _check_order_before_confirm(self, cr, uid, order, context=None):
        super(sale_order, self)._check_order_before_confirm(cr, uid, order, context=context)
        cr.execute( 'SELECT DISTINCT acc.name '\
            'FROM account_analytic_account as acc '\
            'INNER JOIN account_analytic_plan_instance_line as plan_line on (acc.id = plan_line.analytic_account_id) '\
            'INNER JOIN account_analytic_plan_instance as plan on (plan_line.plan_id = plan.id) '\
            'INNER JOIN sale_order_line as sale_line on (plan.id = sale_line.analytics_id AND sale_line.order_id = %s) '\
            'WHERE acc.state in %s', ((tuple([order.id])), ('close','cancelled','pending')))
        contract_list = [rec[0] for rec in cr.fetchall()]
        if contract_list:
            model, action_id = self.pool['ir.model.data'].get_object_reference(cr, uid, 'account', 'action_account_analytic_account_form_closed')
            if action_id:
                msg = _('''Contract(s) mentioned below %s in "Closed/Cancelled/To Renew" state, please renew %s before confirmation :\n%s.''') % (len(contract_list) > 1 and 'are' or 'is', len(contract_list) > 1 and 'them' or 'it', '-' + '\n- '.join(contract_list))
                raise openerp.exceptions.RedirectWarning(msg, action_id, _('Modify Contract(s)'))
        return True

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
