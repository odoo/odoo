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

from osv import osv
from tools.translate import _

class analytic_plan_create_model(osv.osv_memory):
    _name = "analytic.plan.create.model"
    _description = "analytic.plan.create.model"

    def activate(self, cr, uid, ids, context=None):
        plan_obj = self.pool.get('account.analytic.plan.instance')
        mod_obj = self.pool.get('ir.model.data')
        anlytic_plan_obj = self.pool.get('account.analytic.plan')
        if context is None:
            context = {}
        if 'active_id' in context and context['active_id']:
            plan = plan_obj.browse(cr, uid, context['active_id'], context=context)
            if (not plan.name) or (not plan.code):
                raise osv.except_osv(_('Error'), _('Please put a name and a code before saving the model.'))
            pids = anlytic_plan_obj.search(cr, uid, [], context=context)
            if not pids:
                raise osv.except_osv(_('Error'), _('No analytic plan defined.'))
            plan_obj.write(cr, uid, [context['active_id']], {'plan_id':pids[0]}, context=context)

            model_data_ids = mod_obj.search(cr, uid, [('model', '=', 'ir.ui.view'),('name', '=', 'view_analytic_plan_create_model')], context=context)
            resource_id = mod_obj.read(cr, uid, model_data_ids, fields=['res_id'], context=context)[0]['res_id']
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

analytic_plan_create_model()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: