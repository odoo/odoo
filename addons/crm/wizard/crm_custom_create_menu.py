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

from osv import fields,osv


class crm_case_custom_create_menu(osv.osv_memory):
    '''
    Create menu for custom Cases
    '''
    _name = 'crm.custom.create.menu'
    _description = 'Create menu for custom Cases'
    
    _columns = {
        'name': fields.char('Menu Name', size=64, required=True),
        'menu_parent_id': fields.many2one('ir.ui.menu', 'Parent Menu', required=True),
        'section_id': fields.many2one('crm.case.section.custom', 'Section', required=True),
        'view_form': fields.many2one('ir.ui.view', 'Form View', domain=[('type','=','form'),('model','=','crm.case.custom')]),
        'view_tree': fields.many2one('ir.ui.view', 'Tree View', domain=[('type','=','tree'),('model','=','crm.case.custom')]),
        'view_calendar': fields.many2one('ir.ui.view', 'Calendar View', domain=[('type','=','calendar'),('model','=','crm.case.custom')]),
        'view_search': fields.many2one('ir.ui.view', 'Search View', domain=[('type','=','search'),('model','=','crm.case.custom')]),
    }
    
    def menu_create(self, cr, uid, ids, context=None):
        """
        Creates Menus for selected custom section
        """
        data_obj = self.pool.get('ir.model.data')
        for this in self.browse(cr, uid, ids, context=context):
            domain = [('section_id', '=', this.section_id.id)]
            view_mode = [this.view_tree and 'tree', this.view_form and 'form', this.view_calendar and 'calendar']
            view_mode = filter(None , view_mode)
            action_id = self.pool.get('ir.actions.act_window').create(cr,uid, {
                    'name': this.name,
                    'res_model': 'crm.case.custom',
                    'domain': domain,
                    'view_type': 'form',
                    'view_mode': ','.join(view_mode),
                    'search_view_id': this.view_search.id or False, 
                    'context': {'default_section_id': this.section_id.id, 'default_user_id': uid}
                })
            menu_id=self.pool.get('ir.ui.menu').create(cr, uid, {
                'name': this.name,
                'parent_id': this.menu_parent_id.id,
                'icon': 'STOCK_JUSTIFY_FILL'
            })
            self.pool.get('ir.values').create(cr, uid, {
                    'name': 'Custom Cases',
                    'key2': 'tree_but_open',
                    'model': 'ir.ui.menu',
                    'res_id': menu_id,
                    'value': 'ir.actions.act_window,%d'%action_id,
                    'object': True
                })
        return {}

crm_case_custom_create_menu()


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
