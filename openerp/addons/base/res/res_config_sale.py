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

    def default_module_get(self, cr, uid, ids, selectable=[], context=None):
        #TODO: TO BE IMPLEMENTED
        modules = self.pool.get('ir.module.module')
        mods = ['analytic_user_function', 'analytic_journal_billing_rate', 'import_sugarcrm', 'import_google', 'crm_caldav', 'wiki_sale_faq', 'crm_partner_assign', 'plugin_thunderbird', 'plugin_outlook', 'google_map']
        res = dict([(m,False) for m in mods])
        for mod in mods:
            if mod not in selectable:
                selectable.append(mod)
        module_ids = modules.search(cr, uid,
                           [('name','in',selectable),
                            ('state','in',['to install', 'installed', 'to upgrade'])],
                           context=context)
        
        installed_modules = dict([(mod.name,True) for mod in modules.browse(cr, uid, module_ids, context=context)])
        res.update(installed_modules)
        return res

    _defaults = {
        'type': 'pop',
        'google_map': default_module_get,
        'crm_caldav': default_module_get,
        'analytic_user_function': default_module_get,
        'analytic_journal_billing_rate': default_module_get,
        'import_sugarcrm': default_module_get,
        'import_google': default_module_get,
        'wiki_sale_faq': default_module_get,
        'plugin_thunderbird': default_module_get,
        'plugin_outlook': default_module_get,
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

    def execute(self, cr, uid, ids, context=None):
        #TODO: TO BE IMPLEMENTED
        return {}

sale_configuration()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

