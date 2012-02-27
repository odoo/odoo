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

class sale_configuration(osv.osv_memory):
    _name = 'sale.configuration'
    _inherit = 'res.config'

    _columns = {
        'analytic_user_function' : fields.boolean("Use specific User function on Contract/analytic accounts"),
        'analytic_journal_billing_rate' : fields.boolean("Manage Different billing rates on contract/analytic accounts"),
        'import_sugarcrm' : fields.boolean("Import data from sugarCRM?"),
        'import_google' : fields.boolean("Import Contacts & Meetings from Google"),
        'crm_caldav' : fields.boolean("Use caldav to synchronize Meetings"),
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

    def get_applied_groups(self, cr, uid, groups, context=None):
        applied_groups = {}
        user_obj = self.pool.get('res.users')
        dataobj = self.pool.get('ir.model.data')
        group_obj = self.pool.get('res.groups')
        group_ids = []
        groups=[]

        for grp in groups:
            dummy,group_id = dataobj.get_object_reference(cr, 1, 'base', grp);
            group_ids.append(group_id);

        user_group_ids = user_obj.browse(cr, uid, uid, context=context).groups_id

        for group_id in user_group_ids:
            if group_id.id in group_ids:
                groups.append(group_id.id);

        for id in groups:
            key_id = dataobj.search(cr, uid,[('res_id','=',id),('model','=','res.groups')],context=context)
            key = dataobj.browse(cr, uid, key_id[0], context=context).name
            applied_groups.setdefault(key,[]).append('True')

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
        result = super(sale_configuration, self).default_get(
            cr, uid, fields_list, context=context)

        module_list = ['analytic_user_function', 'analytic_journal_billing_rate', 'import_sugarcrm',
                       'import_google', 'crm_caldav', 'wiki_sale_faq', 'crm_partner_assign',
                       'google_map', 'plugin_thunderbird', 'plugin_outlook']

        installed_modules = self.get_installed_modules(cr, uid, module_list, context=context)
        result.update(installed_modules)

        group_list =['group_sale_pricelist_per_customer','group_sale_uom_per_product','group_sale_delivery_address',
                     'group_sale_disc_per_sale_order_line','group_sale_notes_subtotal']

        applied_groups = self.get_applied_groups(cr, uid, group_list, context=context)
        result.update(applied_groups)
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
    
    def write(self, cr, uid, ids, vals, context=None):
        self.execute(cr, uid, ids, context=context)
        return super(sale_configuration, self).write(cr, uid, ids, vals, context=context)

    def execute(self, cr, uid, ids, context=None):
        #TODO: TO BE IMPLEMENTED
        module_obj = self.pool.get('ir.module.module')
        wizard = self.read(cr, uid, ids)[0]
        module_list = ['analytic_user_function', 'analytic_journal_billing_rate', 'import_sugarcrm',
                       'import_google', 'crm_caldav', 'wiki_sale_faq', 'crm_partner_assign',
                       'google_map', 'plugin_thunderbird', 'plugin_outlook']
        for k, v in wizard.items():
            if k in module_list and v == True:
                installed = self.get_installed_modules(cr, uid, [k], context)
                if not installed:
                    module_id = module_obj.search(cr, uid, [('name','=',k)])[0]
                    module_obj.state_update(cr, uid, [module_id], 'to install', ['uninstalled'], context)
                    cr.commit()
                    pooler.restart_pool(cr.dbname, update_module=True)[1]
        

sale_configuration()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

