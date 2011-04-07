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
from osv import fields, osv
import pooler

class base_setup_installer(osv.osv_memory):
    _name = 'base.setup.installer'
    _inherit = 'res.config.installer'

    _install_if = {
        ('sale','crm'): ['sale_crm'],
        ('sale','project'): ['project_mrp'],
    }
    _columns = {
        # Generic modules
        'crm':fields.boolean('Customer Relationship Management',
            help="Helps you track and manage relations with customers such as"
                 " leads, requests or issues. Can automatically send "
                 "reminders, escalate requests or trigger business-specific "
                 "actions based on standard events."),
        'sale':fields.boolean('Sales Management',
            help="Helps you handle your quotations, sale orders and invoicing"
                 "."),
        'project':fields.boolean('Project Management',
            help="Helps you manage your projects and tasks by tracking them, "
                 "generating plannings, etc..."),
        'knowledge':fields.boolean('Knowledge Management',
            help="Lets you install addons geared towards sharing knowledge "
                 "with and between your employees."),
        'stock':fields.boolean('Warehouse Management',
            help="Helps you manage your inventory and main stock operations: delivery orders, receptions, etc."),
        'mrp':fields.boolean('Manufacturing',
            help="Helps you manage your manufacturing processes and generate "
                 "reports on those processes."),
        'account_voucher':fields.boolean('Invoicing',
            help="Allows you to create your invoices and track the payments. It is an easier version of the accounting module for managers who are not accountants."),
        'account_accountant':fields.boolean('Accounting & Finance',
            help="Helps you handle your accounting needs, if you are not an accountant, we suggest you to install only the Invoicing "),
        'purchase':fields.boolean('Purchase Management',
            help="Helps you manage your purchase-related processes such as "
                 "requests for quotations, supplier invoices, etc..."),
        'hr':fields.boolean('Human Resources',
            help="Helps you manage your human resources by encoding your employees structure, generating work sheets, tracking attendance and more."),
        'point_of_sale':fields.boolean('Point of Sales',
            help="Helps you get the most out of your points of sales with "
                 "fast sale encoding, simplified payment mode encoding, "
                 "automatic picking lists generation and more."),
        'marketing':fields.boolean('Marketing',
            help="Helps you manage your marketing campaigns step by step."),
        'profile_tools':fields.boolean('Extra Tools',
            help="Lets you install various interesting but non-essential tools "
                "like Survey, Lunch and Ideas box."),
        'report_designer':fields.boolean('Advanced Reporting',
            help="Lets you install various tools to simplify and enhance "
                 "OpenERP's report creation."),
        # Vertical modules
        'product_expiry':fields.boolean('Food Industry',
            help="Installs a preselected set of OpenERP applications "
                "which will help you manage your industry."),
        'association':fields.boolean('Associations',
            help="Installs a preselected set of OpenERP "
                 "applications which will help you manage your association "
                 "more efficiently."),
        'auction':fields.boolean('Auction Houses',
            help="Installs a preselected set of OpenERP "
                 "applications selected to help you manage your auctions "
                 "as well as the business processes around them."),
        }

    def _if_knowledge(self, cr, uid, ids, context=None):
        if self.pool.get('res.users').browse(cr, uid, uid, context=context)\
               .view == 'simple':
            return ['document_ftp']
        return None

    def _if_misc_tools(self, cr, uid, ids, context=None):
        return ['profile_tools']

    def onchange_moduleselection(self, cr, uid, ids, *args, **kargs):
        value = {}
        # Calculate progress
        closed, total = self.get_current_progress(cr, uid)
        progress = round(100. * closed / (total + len(filter(None, args))))
        value.update({'progress':progress})
        if progress < 10.:
            progress = 10.
        
        return {'value':value}
    

    def default_get(self, cr, uid, fields_list, context=None):
        #Skipping default value as checked for main application, if already installed
        return super(osv.osv_memory, self).default_get(
            cr, uid, fields_list, context=context)

    def fields_get(self, cr, uid, fields=None, context=None, write_access=True):
        #Skipping readonly value for main application, if already installed
        return super(osv.osv_memory, self).fields_get(
            cr, uid, fields, context, write_access)

    def execute(self, cr, uid, ids, context=None):
        if context is None:
             context = {}
        modules = self.pool.get('ir.module.module')
        modules_selected = []
        datas = self.read(cr, uid, ids, context=context)[0]
        key = datas.keys()
        key.remove("id")
        key.remove("progress")
        name_list = []
        for mod in key:
            if datas[mod] == 1:
                modules_selected.append(mod)
        inst = modules.browse(
            cr, uid,
            modules.search(cr, uid,
                           [('name','in',modules_selected)
                            ],
                           context=context),
            context=context)
        for i in inst:
            if i.state == 'uninstalled':
                sect_mod_id = i.id
                modules.state_update(cr, uid, [sect_mod_id], 'to install', ['uninstalled'], context)
                cr.commit()
                new_db, self.pool = pooler.restart_pool(cr.dbname, update_module=True)
            elif i.state == 'installed':
                if modules_selected:
                    for instl in modules_selected:
                        cr.execute("update ir_actions_todo set restart='on_trigger' , state='open' from ir_model_data as data where data.res_id = ir_actions_todo.id and data.model =  'ir.actions.todo' and data.module  like '%"+instl+"%'")
        
        return 
    
base_setup_installer()

#Migrate data from another application Conf wiz

class migrade_application_installer_modules(osv.osv_memory):
    _name = 'migrade.application.installer.modules'
    _inherit = 'res.config.installer'
    _columns = {
        'import_saleforce': fields.boolean('Import Saleforce',
            help="For Import Saleforce"),
        'import_sugarcrm': fields.boolean('Import Sugarcrm',
            help="For Import Sugarcrm"),
        'sync_google_contact': fields.boolean('Sync Google Contact',
            help="For Sync Google Contact"),
        'quickbooks_ippids': fields.boolean('Quickbooks Ippids',
            help="For Quickbooks Ippids"),
    }
    
    _defaults = {
        'import_saleforce': True,
    }

migrade_application_installer_modules()

class product_installer(osv.osv_memory):
    _name = 'product.installer'
    _inherit = 'res.config'
    _columns = {
                'customers': fields.selection([('create','Create'), ('import','Import')], 'Customers', size=32, required=True, help="Import or create customers"),

    }
    _defaults = {
                 'customers': 'create',
    }
    
    def execute(self, cr, uid, ids, context=None):
        if context is None:
             context = {}
        data_obj = self.pool.get('ir.model.data')
        val = self.browse(cr, uid, ids, context=context)[0]
        if val.customers == 'create':
            id2 = data_obj._get_id(cr, uid, 'base', 'view_partner_form')
            if id2:
                id2 = data_obj.browse(cr, uid, id2, context=context).res_id
            return {
                    'view_type': 'form',
                    'view_mode': 'form',
                    'res_model': 'res.partner',
                    'views': [(id2, 'form')],
                    'type': 'ir.actions.act_window',
                    'target': 'current',
                    'nodestroy':False,
                }
        if val.customers == 'import':
            return {'type': 'ir.actions.act_window'}

product_installer()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
