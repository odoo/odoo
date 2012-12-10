# -*- coding: utf-8 -*-
##############################################################################
#    
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2009 Tiny SPRL (<http://tiny.be>).
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

class wizard_model_menu(osv.osv_memory):
    _name = 'wizard.ir.model.menu.create'
    _columns = {
        'menu_id': fields.many2one('ir.ui.menu', 'Parent Menu', required=True),
        'name': fields.char('Menu Name', size=64, required=True),
    }

    def menu_create(self, cr, uid, ids, context=None):
        if not context:
            context = {}
        model_pool = self.pool.get('ir.model')
        for menu in self.browse(cr, uid, ids, context):
            model = model_pool.browse(cr, uid, context.get('model_id'), context=context)
            val = {
                'name': menu.name,
                'res_model': model.model,
                'view_type': 'form',
                'view_mode': 'tree,form'
            }
            action_id = self.pool.get('ir.actions.act_window').create(cr, uid, val)
            self.pool.get('ir.ui.menu').create(cr, uid, {
                'name': menu.name,
                'parent_id': menu.menu_id.id,
                'action': 'ir.actions.act_window,%d' % (action_id,),
                'icon': 'STOCK_INDENT'
            }, context)
        return {'type':'ir.actions.act_window_close'}


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

