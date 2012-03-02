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
        'module_crm_caldav' : fields.boolean("Caldav Synchronization",
                                    help="""Allows Caldav features in Meeting, Share meeting with other calendar clients like sunbird.
                                    It installs crm_caldav module."""),
        'module_fetchmail_crm': fields.boolean("Lead/Opportunity mail gateway", help="""
                                                Allows you to configure your incoming mail server. And creates leads for your mails.
                                               It installs fetchmail_crm module."""),
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
        'module_import_sugarcrm' : fields.boolean("SugarCRM Import",
                                    help="""Import SugarCRM Leads, Opportunities, Users, Accounts, Contacts, Employees, Meetings, Phonecalls, Emails, and Project, Project Tasks Data.
                                    It installs import_sugarcrm module.
                                    """),
        'module_import_google' : fields.boolean("Google Import",
                                    help="""
                                    Import google contact in partner address and add google calendar events details in Meeting.
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
                                        * contacts with possibly different functions for each of its job's addresses.
                                    It installs base_contact module.
                                    """),
        'module_google_map' : fields.boolean("Google maps on customer",
                                    help="""
                                    Allows you to locate customer on Google Map.
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
    
    def create(self, cr, uid, vals, context=None):
        ids = super(crm_configuration, self).create(cr, uid, vals, context=context)
        self.execute(cr, uid, [ids], vals, context=context)
        return ids

    def write(self, cr, uid, ids, vals, context=None):
        self.execute(cr, uid, ids, vals, context=context)
        return super(crm_configuration, self).write(cr, uid, ids, vals, context=context)

    def execute(self, cr, uid, ids, vals, context=None):
        for method in dir(self):
            if method.startswith('set_'):
                getattr(self, method)(cr, uid, ids, vals, context)
        return True

    def get_default_email_configurations(self, cr, uid, ids, context=None):
        ir_values_obj = self.pool.get('ir.values')
        result = {}
        installed_modules = self.get_default_installed_modules(cr, uid, ids, context=context)
        if 'module_fetchmail_crm' in installed_modules.keys():
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
        object_id = model_obj.search(cr, uid, [('model','=','crm.lead')])
        if vals.get('module_fetchmail_crm') and object_id:
            fetchmail_vals = {
                    'name': 'Incoming Leads',
                    'object_id': object_id[0],
                    'server': vals.get('server'),
                    'port': vals.get('port'),
                    'is_ssl': vals.get('is_ssl'),
                    'type': vals.get('type'),
                    'user': vals.get('user'),
                    'password': vals.get('password')
            }
            server_ids = fetchmail_obj.search(cr, uid, [])
            installed_modules = self.get_default_installed_modules(cr, uid, ids, context=context)
            if installed_modules.get('module_fetchmail_crm') or not server_ids:
                server_ids = [fetchmail_obj.create(cr, uid, fetchmail_vals, context=context)]
            else:
                server_ids = fetchmail_obj.search(cr, uid, [('name','=','Incoming Leads')], context=context)
                fetchmail_obj.write(cr, uid, server_ids, fetchmail_vals, context=context)
            fetchmail_obj.button_confirm_login(cr, uid, server_ids, context=None)
            ir_values_obj.set(cr, uid, 'default', False, 'server', ['fetchmail.server'], fetchmail_vals.get('server'))
            ir_values_obj.set(cr, uid, 'default', False, 'port', ['fetchmail.server'], fetchmail_vals.get('port'))
            ir_values_obj.set(cr, uid, 'default', False, 'is_ssl', ['fetchmail.server'], fetchmail_vals.get('is_ssl'))
            ir_values_obj.set(cr, uid, 'default', False, 'type', ['fetchmail.server'], fetchmail_vals.get('type'))
            ir_values_obj.set(cr, uid, 'default', False, 'user', ['fetchmail.server'], fetchmail_vals.get('user'))
            ir_values_obj.set(cr, uid, 'default', False, 'password', ['fetchmail.server'], fetchmail_vals.get('password'))

crm_configuration()