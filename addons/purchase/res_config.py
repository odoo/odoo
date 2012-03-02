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
import pooler
from tools.translate import _

class purchase_configuration(osv.osv_memory):
    _inherit = 'res.config'

    _columns = {
        'default_method' : fields.selection(
            [('manual', 'Based on Purchase Order Lines'),
             ('picking', 'Based on Receptions'),
             ('order', 'Pre-Generate Draft Invoices based on Purchase Orders'),
            ], 'Invoicing Control Method', required=True),
        'module_purchase_analytic_plans': fields.boolean('Purchase Analytic Plan',
                                   help ="""
                                   Allows the user to maintain several analysis plans. These let you split
                                   a line on a supplier purchase order into several accounts and analytic plans.
                                   It installs the purchase_analytic_plans module.
                                   """),
        'module_warning': fields.boolean("Alerts by products or customers",
                                  help="""To trigger warnings in OpenERP objects.
                                  Warning messages can be displayed for objects like sale order, purchase order, picking and invoice. The message is triggered by the form's onchange event.
                                  It installs the warning module."""),
        'module_product_manufacturer': fields.boolean("Define a manufacturer on products",
                        help="""TYou can now define the following for a product:
                            * Manufacturer
                            * Manufacturer Product Name
                            * Manufacturer Product Code
                            * Product Attributes
                        .It installs the product_manufacturer module."""),
        'module_purchase_double_validation': fields.boolean("Configure Limit amount",
                        help="""This allows you double-validation for purchases exceeding minimum amount.
                        It installs the purchase_double_validation module."""),
        'purchase_limit': fields.float('Value'),
        'module_purchase_requisition' : fields.boolean("Track the best price with Purchase Requisition",
                                    help="""When a purchase order is created, you now have the opportunity to save the related requisition.
                                    This new object will regroup and will allow you to easily keep track and order all your purchase orders.
                                    It Installs purchase_requisition module."""),
    }

#    def get_default_installed_modules(self, cr, uid, ids, context=None):
#        installed_modules = super(purchase_configuration, self).get_default_installed_modules(cr, uid, ids, context=context)
#        return installed_modules

#    def get_default_sale_configs(self, cr, uid, ids, context=None):
#        ir_values_obj = self.pool.get('ir.values')
#        data_obj = self.pool.get('ir.model.data')
#        menu_obj = self.pool.get('ir.ui.menu')
#        result = {}
#        invoicing_groups_id = [gid.id for gid in data_obj.get_object(cr, uid, 'sale', 'menu_invoicing_sales_order_lines').groups_id]
#        picking_groups_id = [gid.id for gid in data_obj.get_object(cr, uid, 'sale', 'menu_action_picking_list_to_invoice').groups_id]
#        group_id = data_obj.get_object(cr, uid, 'base', 'group_sale_salesman').id
#        for menu in ir_values_obj.get(cr, uid, 'default', False, ['ir.ui.menu']):
#            if menu[1] == 'groups_id' and group_id in menu[2][0]:
#                if group_id in invoicing_groups_id:
#                    result['sale_orders'] = True
#                if group_id in picking_groups_id:
#                    result['deli_orders'] = True
#        for res in ir_values_obj.get(cr, uid, 'default', False, ['sale.order']):
#            result[res[1]] = res[2]
#        return result
#
#    def default_get(self, cr, uid, fields_list, context=None):
#        result = super(purchase_configuration, self).default_get(
#            cr, uid, fields_list, context=context)
#        for method in dir(self):
#            if method.startswith('get_default_'):
#                result.update(getattr(self, method)(cr, uid, [], context))
#        return result
#
    _defaults = {
        'default_method': lambda s,c,u,ctx: s.pool.get('purchase.order').default_get(c,u,['invoice_method'],context=ctx)['invoice_method'],
    }

    def create(self, cr, uid, vals, context=None):
        ids = super(purchase_configuration, self).create(cr, uid, vals, context=context)
        self.execute(cr, uid, [ids], vals, context=context)
        return ids

    def write(self, cr, uid, ids, vals, context=None):
        self.execute(cr, uid, ids, vals, context=context)
        return super(purchase_configuration, self).write(cr, uid, ids, vals, context=context)

    def execute(self, cr, uid, ids, vals, context=None):
        #TODO: TO BE IMPLEMENTED
        for method in dir(self):
            if method.startswith('set_'):
                getattr(self, method)(cr, uid, ids, vals, context)
        return True

#    def set_installed_modules(self, cr, uid, ids, vals, context=None):
#        if vals.get('task_work'):
#            vals.update({'module_project_timesheet': True, 'module_project_mrp': True})
#        else:
#            vals.update({'module_project_timesheet': False, 'module_project_mrp': False})
#
#        super(sale_configuration, self).set_installed_modules(cr, uid, ids, vals, context=context)

#    def set_sale_defaults(self, cr, uid, ids, vals, context=None):
#        ir_values_obj = self.pool.get('ir.values')
#        data_obj = self.pool.get('ir.model.data')
#        menu_obj = self.pool.get('ir.ui.menu')
#        res = {}
#        wizard = self.browse(cr, uid, ids)[0]
#        group_id = data_obj.get_object(cr, uid, 'base', 'group_sale_salesman').id
#
#        if wizard.sale_orders:
#            menu_id = data_obj.get_object(cr, uid, 'sale', 'menu_invoicing_sales_order_lines').id
#            menu_obj.write(cr, uid, menu_id, {'groups_id':[(4,group_id)]})
#            ir_values_obj.set(cr, uid, 'default', False, 'groups_id', ['ir.ui.menu'], [(4,group_id)])
#
#        if wizard.deli_orders:
#            menu_id = data_obj.get_object(cr, uid, 'sale', 'menu_action_picking_list_to_invoice').id
#            menu_obj.write(cr, uid, menu_id, {'groups_id':[(4,group_id)]})
#            ir_values_obj.set(cr, uid, 'default', False, 'groups_id', ['ir.ui.menu'], [(4,group_id)])
#
#        if wizard.picking_policy:
#            ir_values_obj.set(cr, uid, 'default', False, 'picking_policy', ['sale.order'], 'one')
#
#        if wizard.time_unit:
#            prod_id = data_obj.get_object(cr, uid, 'product', 'product_consultant').id
#            product_obj = self.pool.get('product.product')
#            product_obj.write(cr, uid, prod_id, {'uom_id': wizard.time_unit.id, 'uom_po_id': wizard.time_unit.id})
#
#        ir_values_obj.set(cr, uid, 'default', False, 'order_policy', ['sale.order'], wizard.order_policy)
#        if wizard.task_work and wizard.time_unit:
#            company_id = self.pool.get('res.users').browse(cr, uid, uid).company_id.id
#            self.pool.get('res.company').write(cr, uid, [company_id], {
#                'project_time_mode_id': wizard.time_unit.id
#            }, context=context)
#
#        return res
#
#    def onchange_tax_policy(self, cr, uid, ids, tax_policy, context=None):
#        self.set_tax_policy(cr, uid, ids, {'tax_policy': tax_policy}, context=context)
#        return {'value': {}}
#
#    def set_default_taxes(self, cr, uid, ids, vals, context=None):
#        ir_values_obj = self.pool.get('ir.values')
#        taxes = self._check_default_tax(cr, uid, context=context)
#        if isinstance(vals.get('tax_value'), list):
#            taxes = vals.get('tax_value')
#        if taxes:
#            ir_values_obj.set(cr, uid, 'default', False, 'tax_id', ['sale.order'], taxes[0])
#            ir_values_obj.set(cr, uid, 'default', False, 'tax_id', ['sale.order.line'], taxes)
#            ir_values_obj.set(cr, uid, 'default', False, 'taxes_id', ['product.product'], taxes)

purchase_configuration()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: