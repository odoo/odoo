# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp.osv import osv
from openerp.tools.translate import _

class base_module_configuration(osv.osv_memory):

    _name = "base.module.configuration"

    def start(self, cr, uid, ids, context=None):
        todo_ids = self.pool.get('ir.actions.todo').search(cr, uid,
            ['|', ('type','=','recurring'), ('state', '=', 'open')])
        if not todo_ids:
            # When there is no wizard todo it will display message
            data_obj = self.pool.get('ir.model.data')
            result = data_obj._get_id(cr, uid, 'base', 'view_base_module_configuration_form')
            view_id = data_obj.browse(cr, uid, result).res_id
            value = {
                    'name': _('System Configuration done'), 
                    'view_type': 'form', 
                    'view_mode': 'form', 
                    'res_model': 'base.module.configuration', 
                    'view_id': [view_id], 
                    'type': 'ir.actions.act_window', 
                    'target': 'new'
                }
            return value
        # Run the config wizards
        config_pool = self.pool.get('res.config')
        return config_pool.start(cr, uid, ids, context=context)

base_module_configuration()
