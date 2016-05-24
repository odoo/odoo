# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp.osv import fields, osv
from openerp.exceptions import UserError
from openerp.tools.translate import _


class project_task(osv.osv):
    _name = "project.task"
    _inherit = "project.task"
    _columns = {
        'procurement_id': fields.many2one('procurement.order', 'Procurement', ondelete='set null'),
        'sale_line_id': fields.related('procurement_id', 'sale_line_id', type='many2one', relation='sale.order.line', store=True, string='Sales Order Line'),
    }

    def unlink(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        for task in self.browse(cr, uid, ids, context=context):
            if task.sale_line_id:
                raise UserError(_('You cannot delete a task related to a Sale Order. You can only archive this task.'))
        res = super(project_task, self).unlink(cr, uid, ids, context)
        return res

    def action_view_so(self, cr, uid, ids, context=None):
        task = self.browse(cr, uid, ids, context=context)[0]
        return {
            "type": "ir.actions.act_window",
            "res_model": "sale.order",
            "views": [[False, "form"]],
            "res_id": task.sale_line_id.order_id.id,
            "context": {"create": False, "show_sale": True},
        }

    def onchange_parent_id(self, cr, uid, ids, parent_id, context=None):
        if not parent_id:
            return {'value' : {'procurement_id': False, 'sale_line_id': False }}
        parent_task = self.browse(cr, uid, parent_id, context=context)
        return {
            'value' : {
                'procurement_id' : parent_task.procurement_id.id,
                'sale_line_id' : parent_task.sale_line_id.id,
            }
        }
