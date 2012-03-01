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

from osv import fields, osv
from tools.translate import _

class account_configuration(osv.osv_memory):
    _inherit = 'res.config'

    _columns = {
            'tax_policy': fields.selection([
                ('no_tax', 'No Tax'),
                ('global_on_order', 'Global On Order'),
                ('on_order_line', 'On Order Lines'),
            ], 'Taxes', required=True),
            'tax_value': fields.float('Value'),
    }
    
    _defaults = {
        'tax_policy': 'global_on_order',
    }

    def get_default_tax_policy(self, cr, uid, ids, context=None):
        applied_groups = self.get_default_applied_groups(cr, uid, ids, context=context)
        if applied_groups.get('group_sale_taxes_global_on_order'):
            applied_groups.update({'tax_policy': 'global_on_order'})
        elif applied_groups.get('group_sale_taxes_on_order_line'):
            applied_groups.update({'tax_policy': 'on_order_line'})
        else:
            applied_groups.update({'tax_policy': 'no_tax'})
        return applied_groups

    def _check_default_tax(self, cr, uid, context=None):
        ir_values_obj = self.pool.get('ir.values')
        for tax in ir_values_obj.get(cr, uid, 'default', False, ['product.product']):
            if tax[1] == 'taxes_id':
                return tax[2]
        return False

    def default_get(self, cr, uid, fields_list, context=None):
        ir_values_obj = self.pool.get('ir.values')
        res = super(account_configuration, self).default_get(cr, uid, fields_list, context=context)
        res.update({'tax_value': 15.0})
        tax_id = self._check_default_tax(cr, uid, context)
        if tax_id:
            res.update({'tax_value': tax_id and tax_id[0]})
        return res
    
    def fields_view_get(self, cr, uid, view_id=None, view_type='form', context=None, toolbar=False, submenu=False):
        ir_values_obj = self.pool.get('ir.values')
        res = super(account_configuration, self).fields_view_get(cr, uid, view_id, view_type, context, toolbar, submenu)
        if self._check_default_tax(cr, uid, context) and res['fields'].get('tax_value'):
            res['fields']['tax_value'] = {'domain': [], 'views': {}, 'context': {}, 'selectable': True, 'type': 'many2one', 'relation': 'account.tax', 'string': 'Value'}
        return res

    def set_tax_policy(self, cr, uid, ids, vals, context=None):
        data_obj = self.pool.get('ir.model.data')
        users_obj = self.pool.get('res.users')
        groups_obj = self.pool.get('res.groups')
        ir_values_obj = self.pool.get('ir.values')
        dummy,user_group_id = data_obj.get_object_reference(cr, uid, 'base', 'group_user')
        tax_policy = vals.get('tax_policy')
        order_group_id = data_obj.get_object(cr, uid, 'base', 'group_sale_taxes_global_on_order').id
        order_line_group_id = data_obj.get_object(cr, uid, 'base', 'group_sale_taxes_on_order_line').id
        group_id = False
        remove_group_id = False

        if tax_policy == 'global_on_order':
            group_id = order_group_id
            remove_group_id = order_line_group_id
        elif tax_policy == 'on_order_line':
            group_id = order_line_group_id
            remove_group_id = order_group_id

        if group_id:
            groups_obj.write(cr, uid, [user_group_id], {'implied_ids': [(4,group_id)]})
            users_obj.write(cr, uid, [uid], {'groups_id': [(4,group_id)]})
            ir_values_obj.set(cr, uid, 'default', False, 'groups_id', ['res.users'], [(4,group_id)])
            groups_obj.write(cr, uid, [user_group_id], {'implied_ids': [(3,remove_group_id)]})
            users_obj.write(cr, uid, [uid], {'groups_id': [(3,remove_group_id)]})
            ir_values_obj.set(cr, uid, 'default', False, 'groups_id', ['res.users'], [(3,remove_group_id)])
        else:
            groups = [order_group_id, remove_group_id]
            for group_id in groups:
                groups_obj.write(cr, uid, [user_group_id], {'implied_ids': [(3,group_id)]})
                users_obj.write(cr, uid, [uid], {'groups_id': [(3,group_id)]})
                ir_values_obj.set(cr, uid, 'default', False, 'groups_id', ['res.users'], [(3,group_id)])

account_configuration()