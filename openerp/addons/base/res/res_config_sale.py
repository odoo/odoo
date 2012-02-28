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

MODULE_LIST = [
               'analytic_user_function', 'analytic_journal_billing_rate', 'import_sugarcrm',
               'import_google', 'crm_caldav', 'wiki_sale_faq', 'base_contact','sale_layout','warning',
               'google_map', 'fetchmail_crm', 'plugin_thunderbird', 'plugin_outlook','account_analytic_analysis'
]

class sale_configuration(osv.osv_memory):
    _name = 'sale.configuration'
    _inherit = 'res.config'

    _columns = {
        'analytic_user_function' : fields.boolean("User function by contracts",
                                    help="Install analytic_user_function module:This module allows you to define what is the default function of a specific user on a given account"),
        'analytic_journal_billing_rate' : fields.boolean("Billing rates by contracts",
                                    help="Install analytic_journal_billing_rate module: This module allows you to define what is the default invoicing rate for a specific journal on a given account."),
        'import_sugarcrm' : fields.boolean("Import data from sugarCRM?",
                                    help="Install import_sugarcrm module: This Module Import SugarCRM Leads, Opportunities, Users, Accounts, Contacts, Employees, Meetings, Phonecalls, Emails, and Project, Project Tasks Data into OpenERP Module."),
        'import_google' : fields.boolean("Import Contacts & Meetings from Google",
                                    help="Install import_google module: The module adds google contact in partner address and add google calendar events details in Meeting"),
        'crm_caldav' : fields.boolean("Use caldav to synchronize Meetings",
                                    help="Install crm_caldav module: Caldav features in Meeting"),
        'wiki_sale_faq' : fields.boolean("Install a sales FAQ?",
                                    help="Install wiki_sale_faq module: This module provides a Wiki Sales FAQ Template."),
        'base_contact' : fields.boolean("Manage a several address per customer",
                                    help="Install crm_partner_assign module: This is the module used by OpenERP SA to redirect customers to its partners, based on geolocalization."),
        'google_map' : fields.boolean("Google maps on customer",
                                    help="Install google_map module: The module adds Google Map field in partner address."),
        'fetchmail_crm': fields.boolean("Lead/Opportunity mail gateway"),
        'server' : fields.char('Server Name', size=256),
        'port' : fields.integer('Port'),
        'type':fields.selection([
                   ('pop', 'POP Server'),
                   ('imap', 'IMAP Server'),
                   ('local', 'Local Server'),
               ], 'Server Type'),
        'is_ssl': fields.boolean('SSL/TLS', help="Connections are encrypted with SSL/TLS through a dedicated port (default: IMAPS=993, POP=995)"),
        'user' : fields.char('Username', size=256),
        'password' : fields.char('Password', size=1024),
        'plugin_thunderbird': fields.boolean('Thunderbird plugin',
                                    help="Install plugin_thunderbird module: This module is required for the Thuderbird Plug-in to work properly."),
        'plugin_outlook': fields.boolean('Outlook plugin',
                                    help="Install plugin_outlook module: This module provides the Outlook Plug-in."),
        'account_analytic_analysis': fields.boolean('Contracts',
                                    help="Install account_analytic_analysis module: This module is for modifying account analytic view to show important data to project manager of services companies."),
    }

    def get_applied_groups(self, cr, uid, context=None):
        applied_groups = {}
        user_obj = self.pool.get('res.users')
        dataobj = self.pool.get('ir.model.data')

        groups = []
        user_group_ids = user_obj.browse(cr, uid, uid, context=context).groups_id

        for group_id in user_group_ids:
            groups.append(group_id.id)

        for id in groups:
            key_id = dataobj.search(cr, uid,[('res_id','=',id),('model','=','res.groups')],context=context)
            key = dataobj.browse(cr, uid, key_id[0], context=context).name
            applied_groups[key] = True

        return applied_groups

    def get_installed_modules(self, cr, uid, modules, context=None):
        module_obj = self.pool.get('ir.module.module')
        module_ids = module_obj.search(cr, uid,
                           [('name','in',modules),
                            ('state','in',['to install', 'installed', 'to upgrade'])],
                           context=context)
        installed_modules = dict([(mod.name,True) for mod in module_obj.browse(cr, uid, module_ids, context=context)])
        return installed_modules

    def default_get(self, cr, uid, fields_list, context=None):
        ir_values_obj = self.pool.get('ir.values')
        result = super(sale_configuration, self).default_get(
            cr, uid, fields_list, context=context)
        installed_modules = self.get_installed_modules(cr, uid, MODULE_LIST, context=context)
        result.update(installed_modules)

        if 'fetchmail_crm' in installed_modules.keys():
            for val in ir_values_obj.get(cr, uid, 'default', False, ['fetchmail.server']):
                result.update({val[1]: val[2]})

        return result

    _defaults = {
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
        return {'value': values}
    
    def create(self, cr, uid, vals, context=None):
        ids = super(sale_configuration, self).create(cr, uid, vals, context=context)
        self.execute(cr, uid, [ids], vals, context=context)
        return ids 
    
    def write(self, cr, uid, ids, vals, context=None):
        self.execute(cr, uid, ids, vals, context=context)
        return super(sale_configuration, self).write(cr, uid, ids, vals, context=context)

    def execute(self, cr, uid, ids, vals, context=None):
        #TODO: TO BE IMPLEMENTED
        module_obj = self.pool.get('ir.module.module')
        model_obj = self.pool.get('ir.model')
        fetchmail_obj = self.pool.get('fetchmail.server')
        ir_values_obj = self.pool.get('ir.values')
        for k, v in vals.items():
            if k in MODULE_LIST:
                installed = self.get_installed_modules(cr, uid, [k], context)
                if v == True and not installed:
                    module_id = module_obj.search(cr, uid, [('name','=',k)])[0]
                    module_obj.state_update(cr, uid, [module_id], 'to install', ['uninstalled'], context)
                    cr.commit()
                    pooler.restart_pool(cr.dbname, update_module=True)[1]
                elif v == False and installed.get(k):
                    module_id = module_obj.search(cr, uid, [('name','=',k)])[0]
                    module_obj.state_update(cr, uid, [module_id], 'to remove', ['installed'], context)
                    cr.commit()
                    pooler.restart_pool(cr.dbname, update_module=True)[1]
                    
        if vals.get('fetchmail_crm'):
            object_id = model_obj.search(cr, uid, [('model','=','crm.lead')])[0]
            fetchmail_vals = {
                    'name': 'Incoming Leads',
                    'object_id': object_id,
                    'server': vals.get('server'),
                    'port': vals.get('port'),
                    'is_ssl': vals.get('is_ssl'),
                    'type': vals.get('type'),
                    'user': vals.get('user'),
                    'password': vals.get('password')
            }
            if not self.get_installed_modules(cr, uid, ['fetchmail_crm'], context):
                fetchmail_obj.create(cr, uid, fetchmail_vals, context=context)
            else:
                fetchmail_ids = fetchmail_obj.search(cr, uid, [('name','=','Incoming Leads')], context=context)
                fetchmail_obj.write(cr, uid, fetchmail_ids, fetchmail_vals, context=context)
            ir_values_obj.set(cr, uid, 'default', False, 'server', ['fetchmail.server'], fetchmail_vals.get('server'))
            ir_values_obj.set(cr, uid, 'default', False, 'port', ['fetchmail.server'], fetchmail_vals.get('port'))
            ir_values_obj.set(cr, uid, 'default', False, 'is_ssl', ['fetchmail.server'], fetchmail_vals.get('is_ssl'))
            ir_values_obj.set(cr, uid, 'default', False, 'type', ['fetchmail.server'], fetchmail_vals.get('type'))
            ir_values_obj.set(cr, uid, 'default', False, 'user', ['fetchmail.server'], fetchmail_vals.get('user'))
            ir_values_obj.set(cr, uid, 'default', False, 'password', ['fetchmail.server'], fetchmail_vals.get('password'))

sale_configuration()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

