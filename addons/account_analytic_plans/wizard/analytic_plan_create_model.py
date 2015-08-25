# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp.osv import osv
from openerp.tools.translate import _
from openerp.exceptions import UserError

class analytic_plan_create_model(osv.osv_memory):
    _name = "analytic.plan.create.model"
    _description = "analytic.plan.create.model"

    def activate(self, cr, uid, ids, context=None):
        plan_obj = self.pool.get('account.analytic.plan.instance')
        anlytic_plan_obj = self.pool.get('account.analytic.plan')
        if context is None:
            context = {}
        if 'active_id' in context and context['active_id']:
            plan = plan_obj.browse(cr, uid, context['active_id'], context=context)
            if (not plan.name) or (not plan.code):
                raise UserError(_('Please put a name and a code before saving the model.'))
            pids = anlytic_plan_obj.search(cr, uid, [], context=context)
            if not pids:
                raise UserError(_('There is no analytic plan defined.'))
            plan_obj.write(cr, uid, [context['active_id']], {'plan_id':pids[0]}, context=context)

            resource_id = self.pool['ir.model.data'].xmlid_to_res_id(
                cr, uid, 'account.view_analytic_plan_create_model',
                context=context, raise_if_not_found=True)
            return {
                'name': _('Distribution Model Saved'),
                'view_type': 'form',
                'view_mode': 'tree,form',
                'res_model': 'analytic.plan.create.model',
                'views': [(resource_id,'form')],
                'type': 'ir.actions.act_window',
                'target': 'new',
            }
        else:
            return {'type': 'ir.actions.act_window_close'}
