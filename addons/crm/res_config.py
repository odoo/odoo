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

class crm_configuration(osv.osv_memory):
    _inherit = 'res.config'

    _columns = {
        'module_crm_caldav' : fields.boolean("Use caldav to synchronize Meetings",
                                    help="Install crm_caldav module: Caldav features in Meeting"),
        'fetchmail_crm': fields.boolean("Lead/Opportunity mail gateway"),
        'server' : fields.char('Server Name', size=256),
        'port' : fields.integer('Port'),
        'type': fields.selection([
                   ('pop', 'POP Server'),
                   ('imap', 'IMAP Server'),
                   ('local', 'Local Server'),
               ], 'Server Type'),
        'is_ssl': fields.boolean('SSL/TLS', help="Connections are encrypted with SSL/TLS through a dedicated port (default: IMAPS=993, POP=995)"),
        'user' : fields.char('Username', size=256),
        'password' : fields.char('Password', size=1024),
        'module_import_sugarcrm' : fields.boolean("Import data from sugarCRM?",
                                    help="""Import SugarCRM Leads, Opportunities, Users, Accounts, Contacts, Employees, Meetings, Phonecalls, Emails, and Project, Project Tasks Data into OpenERP Module.
                                    It installs import_sugarcrm module.
                                    """),
        'module_import_google' : fields.boolean("Import Contacts & Meetings from Google",
                                    help="""
                                    Import google contact in partner address and add google calendar events details in Meeting
                                    It installs import_google module.
                                    """),
        'module_wiki_sale_faq' : fields.boolean("Install a sales FAQ?",
                                    help="""
                                    It provides demo data, thereby creating a Wiki Group and a Wiki Page for Wiki Sale FAQ.
                                    It installs wiki_sale_faq module.
                                    """),
        'module_base_contact' : fields.boolean("Manage a several address per customer",
                                    help="""
                                    It lets you define:
                                        * contacts unrelated to a partner,
                                        * contacts working at several addresses (possibly for different partners),
                                        * contacts with possibly different functions for each of its job's addresses
                                    It installs base_contact module.
                                    """),
        'module_google_map' : fields.boolean("Google maps on customer",
                                    help="""
                                    This allows yopu to locate customer on Google Map
                                    It installs google_map module.
                                    """),
        'module_plugin_thunderbird': fields.boolean('Thunderbird plugin',
                                    help="""
                                    The plugin allows you archive email and its attachments to the selected
                                    OpenERP objects. You can select a partner, a task, a project, an analytical
                                    account, or any other object and attach the selected mail as a .eml file in
                                    the attachment of a selected record. You can create documents for CRM Lead,
                                    HR Applicant and Project Issue from selected mails.
                                    It installs plugin_thunderbird module.
                                    """),
        'module_plugin_outlook': fields.boolean('Outlook plugin',
                                    help="""
                                    Outlook plug-in allows you to select an object that you would like to add
                                    to your email and its attachments from MS Outlook. You can select a partner, a task,
                                    a project, an analytical account, or any other object and archive selected
                                    mail into mail.message with attachments.
                                    It installs plugin_outlook module.
                                    """),
    }

    _defaults = {
        'type': 'pop',
    }

    def get_default_email_configurations(self, cr, uid, ids, context=None):
        ir_values_obj = self.pool.get('ir.values')
        result = {}
        installed_modules = self.get_default_installed_modules(cr, uid, ids, context=context)
        if 'fetchmail_crm' in installed_modules.keys():
            for val in ir_values_obj.get(cr, uid, 'default', False, ['fetchmail.server']):
                result.update({val[1]: val[2]})
        return result
    
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
    
    def set_email_configurations(self, cr, uid, ids, vals, context=None):
        model_obj = self.pool.get('ir.model')
        fetchmail_obj = self.pool.get('fetchmail.server')
        ir_values_obj = self.pool.get('ir.values')
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
            server_ids = fetchmail_obj.search(cr, uid, [])
            if not self.get_default_installed_modules(cr, uid, ['fetchmail_crm'], context) or not server_ids:
                tt = fetchmail_obj.create(cr, uid, fetchmail_vals, context=context)
            else:
                fetchmail_ids = fetchmail_obj.search(cr, uid, [('name','=','Incoming Leads')], context=context)
                fetchmail_obj.write(cr, uid, fetchmail_ids, fetchmail_vals, context=context)
            ir_values_obj.set(cr, uid, 'default', False, 'server', ['fetchmail.server'], fetchmail_vals.get('server'))
            ir_values_obj.set(cr, uid, 'default', False, 'port', ['fetchmail.server'], fetchmail_vals.get('port'))
            ir_values_obj.set(cr, uid, 'default', False, 'is_ssl', ['fetchmail.server'], fetchmail_vals.get('is_ssl'))
            ir_values_obj.set(cr, uid, 'default', False, 'type', ['fetchmail.server'], fetchmail_vals.get('type'))
            ir_values_obj.set(cr, uid, 'default', False, 'user', ['fetchmail.server'], fetchmail_vals.get('user'))
            ir_values_obj.set(cr, uid, 'default', False, 'password', ['fetchmail.server'], fetchmail_vals.get('password'))

crm_configuration()