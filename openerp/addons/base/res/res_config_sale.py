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

from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
import time
import pooler
from osv import fields, osv
from tools.translate import _
from tools import DEFAULT_SERVER_DATE_FORMAT, DEFAULT_SERVER_DATETIME_FORMAT, float_compare
import decimal_precision as dp
import netsvc

class sale_config_picking_policy(osv.osv_memory):
    _name = 'sale.config.picking_policy'
    _inherit = 'res.config'

    _columns = {
        'name': fields.char('Name', size=64),
        'sale_orders': fields.boolean('Based on Sales Orders',),
        'deli_orders': fields.boolean('Based on Delivery Orders'),
        'task_work': fields.boolean('Based on Tasks\' Work'),
        'timesheet': fields.boolean('Based on Timesheet'),
        'order_policy': fields.selection([
            ('manual', 'Invoice Based on Sales Orders'),
            ('picking', 'Invoice Based on Deliveries'),
        ], 'Main Method Based On', required=True, help="You can generate invoices based on sales orders or based on shippings."),
        'charge_delivery': fields.boolean('Do you charge the delivery?'),
        'picking_policy' : fields.boolean("Deliver all products at once?"),
        'group_sale_pricelist_per_customer':fields.boolean("Activate pricelist to manage prices per customer "),
        'group_sale_uom_per_product':fields.boolean("Allow different unit of measure per product"),
        'group_sale_delivery_address':fields.boolean(" Allow delivery address different from invoice address"),
        'group_sale_disc_per_sale_order_line':fields.boolean("Allow to apply discounts per sale order lines "),
        'group_sale_notes_subtotal':fields.boolean("Allow notes and subtotals"),
        'group_sale_alerts_per_customer_products':fields.boolean("Allow to define alerts by products or customers"),
        'tax_value' : fields.float('Value'),
        'tax_policy': fields.selection([
            ('no_tax', 'No Tax'),
            ('global_on_order', 'Global On Order'),
            ('on_order_line', 'On Order Lines'),
        ], 'Taxes'),
        'sale_margin' : fields.boolean("Display Margin For Users"),
        'sale_journal' : fields.boolean("Invoice_journal?"),
        'analytic_user_function' : fields.boolean("Use specific User function on Contract/analytic accounts"),
        'analytic_journal_billing_rate' : fields.boolean("Manage Different billing rates on contract/analytic accounts"),
        'import_sugarcrm' : fields.boolean("Import data from sugarCRM?"),
        'import_google' : fields.boolean("Import Contacts & Meetings from Google"),
        'crm_caldav' : fields.boolean("Use caldev to synchronize Meetings"),
        'wiki_sale_faq' : fields.boolean("Install a sales FAQ?"),
        'crm_partner_assign' : fields.boolean("Manage a several address per customer"),
        'google_map' : fields.boolean("Google maps on customer"),
        'create_leads': fields.boolean("Create Leads from an Email Account"),
        'server' : fields.char('Server Name', size=256, required=True),
        'port' : fields.integer('Port', required=True),
        'type':fields.selection([
                   ('pop', 'POP Server'),
                   ('imap', 'IMAP Server'),
                   ('local', 'Local Server'),
               ], 'Server Type', required=True),
        'is_ssl': fields.boolean('SSL/TLS', help="Connections are encrypted with SSL/TLS through a dedicated port (default: IMAPS=993, POP=995)"),
        'user' : fields.char('Username', size=256, required=True),
        'password' : fields.char('Password', size=1024, required=True),
        'plugin_thunderbird': fields.boolean('Push your email from Thunderbird to an OpenERP document'),
        'plugin_outlook': fields.boolean('Push your email from Outlook to an OpenERP document'),

    }
    _defaults = {
        'order_policy': 'manual',
        'tax_policy': 'no_tax',
        'type': 'pop',
    }
    
    def onchange_server_type(self, cr, uid, ids, server_type=False, ssl=False):
        port = 0
        values = {}
        if server_type == 'pop':
            port = ssl and 995 or 110
        elif server_type == 'imap':
            port = ssl and 993 or 143
        else:
            values['server'] = ''
        values['port'] = port
        return {'value':values}

    def onchange_order(self, cr, uid, ids, sale, deli, context=None):
        res = {}
        if sale:
            res.update({'order_policy': 'manual'})
        elif deli:
            res.update({'order_policy': 'picking'})
        return {'value':res}

    def execute(self, cr, uid, ids, context=None):
        ir_values_obj = self.pool.get('ir.values')
        data_obj = self.pool.get('ir.model.data')
        menu_obj = self.pool.get('ir.ui.menu')
        module_obj = self.pool.get('ir.module.module')
        module_upgrade_obj = self.pool.get('base.module.upgrade')
        module_name = []

        group_id = data_obj.get_object(cr, uid, 'base', 'group_sale_salesman').id

        wizard = self.browse(cr, uid, ids)[0]

        if wizard.sale_orders:
            menu_id = data_obj.get_object(cr, uid, 'sale', 'menu_invoicing_sales_order_lines').id
            menu_obj.write(cr, uid, menu_id, {'groups_id':[(4,group_id)]})

        if wizard.deli_orders:
            menu_id = data_obj.get_object(cr, uid, 'sale', 'menu_action_picking_list_to_invoice').id
            menu_obj.write(cr, uid, menu_id, {'groups_id':[(4,group_id)]})

        if wizard.task_work:
            module_name.append('project_timesheet')
            module_name.append('project_mrp')
            module_name.append('account_analytic_analysis')

        if wizard.timesheet:
            module_name.append('account_analytic_analysis')

        if wizard.charge_delivery:
            module_name.append('delivery')

        if len(module_name):
            module_ids = []
            need_install = False
            module_ids = []
            for module in module_name:
                data_id = module_obj.name_search(cr, uid , module, [], '=')
                module_ids.append(data_id[0][0])

            for module in module_obj.browse(cr, uid, module_ids):
                if module.state == 'uninstalled':
                    module_obj.state_update(cr, uid, [module.id], 'to install', ['uninstalled'], context)
                    need_install = True
                    cr.commit()
            if need_install:
                pooler.restart_pool(cr.dbname, update_module=True)[1]

#        if wizard.time_unit:
#            prod_id = data_obj.get_object(cr, uid, 'product', 'product_consultant').id
#            product_obj = self.pool.get('product.product')
#            product_obj.write(cr, uid, prod_id, {'uom_id':wizard.time_unit.id, 'uom_po_id': wizard.time_unit.id})

        ir_values_obj.set(cr, uid, 'default', False, 'order_policy', ['sale.order'], wizard.order_policy)
        if wizard.task_work and wizard.time_unit:
            company_id = self.pool.get('res.users').browse(cr, uid, uid).company_id.id
            self.pool.get('res.company').write(cr, uid, [company_id], {
                'project_time_mode_id': wizard.time_unit.id
            }, context=context)

    def apply_cb(self, cr, uid, ids, context=None):
        ir_values_obj = self.pool.get('ir.values')
        wizard = self.browse(cr, uid, ids, context=context)[0]
        ir_values_obj.set(cr, uid, 'default', False, 'picking_policy', ['sale.order'], wizard.picking_policy)
        return {'type' : 'ir.actions.act_window_close'}

sale_config_picking_policy()



#class define_delivery_steps(osv.osv_memory):
#    _name = 'delivery.define.delivery.steps.wizard'
#
#    _columns = {
#        'picking_policy' : fields.selection([('direct', 'Deliver each product when available'), ('one', 'Deliver all products at once')], 'Picking Policy'),
#    }
#    _defaults = {
#        'picking_policy': lambda s,c,u,ctx: s.pool.get('sale.order').default_get(c,u,['picking_policy'],context=ctx)['picking_policy']
#    }
#
#    def apply_cb(self, cr, uid, ids, context=None):
#        ir_values_obj = self.pool.get('ir.values')
#        wizard = self.browse(cr, uid, ids, context=context)[0]
#        ir_values_obj.set(cr, uid, 'default', False, 'picking_policy', ['sale.order'], wizard.picking_policy)
#        return {'type' : 'ir.actions.act_window_close'}
#
#define_delivery_steps()