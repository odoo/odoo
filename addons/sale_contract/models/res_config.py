# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp.osv import fields, osv
from openerp.tools.translate import _
from openerp.exceptions import UserError

class sale_configuration(osv.osv_memory):
    _inherit = 'sale.config.settings'

    _columns = {
        'group_template_required': fields.boolean("Mandatory use of templates.",
            implied_group='sale_contract.group_template_required',
            help="Allows you to set the template field as required when creating an analytic account or a contract."),
        'time_unit': fields.many2one('product.uom', 'The default working time unit.'),
    }

    def default_get(self, cr, uid, fields, context=None):
        ir_model_data = self.pool.get('ir.model.data')
        res = super(sale_configuration, self).default_get(cr, uid, fields, context)
        if res.get('module_project'):
            user = self.pool.get('res.users').browse(cr, uid, uid, context)
            res['time_unit'] = user.company_id.project_time_mode_id.id
        res['timesheet'] = res.get('module_sale_contract')
        return res

    def set_sale_defaults(self, cr, uid, ids, context=None):
        ir_model_data = self.pool.get('ir.model.data')
        wizard = self.browse(cr, uid, ids)[0]

        if wizard.module_project and wizard.time_unit:
            user = self.pool.get('res.users').browse(cr, uid, uid, context)
            user.company_id.write({'project_time_mode_id': wizard.time_unit.id})
        res = super(sale_configuration, self).set_sale_defaults(cr, uid, ids, context)
        return res
