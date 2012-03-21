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
    _inherit = 'sale.config.settings'

    _columns = {
        'module_crm_caldav': fields.boolean("Caldav Synchronization",
            help="""Use protocol caldav to synchronize meetings with other calendar applications (like Sunbird).
                This installs the module crm_caldav."""),
        'fetchmail_crm': fields.boolean("Lead/Opportunity mail gateway",
            help="Create leads automatically from an email gateway."),
        'default_server': fields.char('Server Name', size=256),
        'default_port': fields.integer('Port'),
        'default_type': fields.selection([
                ('pop', 'POP Server'),
                ('imap', 'IMAP Server'),
                ('local', 'Local Server'),
            ], 'Server Type'),
        'default_is_ssl': fields.boolean('SSL/TLS',
            help="Connections are encrypted with SSL/TLS through a dedicated port (default: IMAPS=993, POP=995)"),
        'default_user': fields.char('Username', size=256),
        'default_password': fields.char('Password', size=1024),
        'module_import_sugarcrm': fields.boolean("SugarCRM Import",
            help="""Import SugarCRM leads, opportunities, users, accounts, contacts, employees, meetings, phonecalls, emails, project and project tasks data.
                This installs the module import_sugarcrm."""),
        'module_import_google': fields.boolean("Google Import",
            help="""Import google contact in partner address and add google calendar events details in Meeting.
                This installs the module import_google."""),
        'module_wiki_sale_faq': fields.boolean("Install a sales FAQ",
            help="""This provides demo data, thereby creating a Wiki Group and a Wiki Page for Wiki Sale FAQ.
                This installs the module wiki_sale_faq."""),
        'module_base_contact': fields.boolean("Manage a several addresses per customer",
            help="""Lets you define:
                    * contacts unrelated to a partner,
                    * contacts working at several addresses (possibly for different partners),
                    * contacts with possibly different job functions.
                This installs the module base_contact."""),
        'module_google_map': fields.boolean("Google maps on customer",
            help="""Locate customers on Google Map.
                This installs the module google_map."""),
    }

    _defaults = {
        'default_type': 'pop',
    }

    def onchange_server_type(self, cr, uid, ids, server_type, ssl, context=None):
        values = {}
        if server_type == 'pop':
            values['default_port'] = ssl and 995 or 110
        elif server_type == 'imap':
            values['default_port'] = ssl and 993 or 143
        else:
            values['default_server'] = False
            values['default_port'] = 0
        return {'value': values}

    def get_default_email_configurations(self, cr, uid, ids, context=None):
        ir_values = self.pool.get('ir.values')
        server_count = self.pool.get('fetchmail.server').search(cr, uid,
                        [('name','=','Incoming Leads'), ('state','=','done')], count=True)
        return {
            'fetchmail_crm': bool(server_count),
            'default_server': ir_values.get_default(cr, uid, 'fetchmail.server', 'server') or False,
            'default_port': ir_values.get_default(cr, uid, 'fetchmail.server', 'port') or False,
            'default_type': ir_values.get_default(cr, uid, 'fetchmail.server', 'type') or False,
            'default_is_ssl': ir_values.get_default(cr, uid, 'fetchmail.server', 'is_ssl') or False,
            'default_user': ir_values.get_default(cr, uid, 'fetchmail.server', 'user') or False,
            'default_password': ir_values.get_default(cr, uid, 'fetchmail.server', 'password') or False,
        }

    def set_email_configurations(self, cr, uid, ids, context=None):
        ir_values = self.pool.get('ir.values')
        fetchmail_obj = self.pool.get('fetchmail.server')
        config = self.browse(cr, uid, ids[0], context)
        model_ids = self.pool.get('ir.model').search(cr, uid, [('model', '=', 'crm.lead')])
        if config.fetchmail_crm and model_ids:
            fetchmail_vals = {
                    'name': 'Incoming Leads',
                    'object_id': model_ids[0],
                    'server': config.default_server,
                    'port': config.default_port,
                    'is_ssl': config.default_is_ssl,
                    'type': config.default_type,
                    'user': config.default_user,
                    'password': config.default_password,
            }
            server_ids = fetchmail_obj.search(cr, uid, [('name','=','Incoming Leads'), ('state','=','done')])
            if not server_ids:
                server_ids = [fetchmail_obj.create(cr, uid, fetchmail_vals, context=context)]
            else:
                server_ids = fetchmail_obj.search(cr, uid, [('name','=','Incoming Leads')], context=context)
                fetchmail_obj.write(cr, uid, server_ids, fetchmail_vals, context=context)
            fetchmail_obj.button_confirm_login(cr, uid, server_ids, context=None)
            ir_values.set_default(cr, uid, 'fetchmail.server', 'server', config.default_server)
            ir_values.set_default(cr, uid, 'fetchmail.server', 'port', config.default_port)
            ir_values.set_default(cr, uid, 'fetchmail.server', 'is_ssl', config.default_is_ssl)
            ir_values.set_default(cr, uid, 'fetchmail.server', 'type', config.default_type)
            ir_values.set_default(cr, uid, 'fetchmail.server', 'user', config.default_user)
            ir_values.set_default(cr, uid, 'fetchmail.server', 'password', config.default_password)
        else:
            server_ids = fetchmail_obj.search(cr, uid, [('name','=','Incoming Leads'), ('state','=','done')])
            fetchmail_obj.set_draft(cr, uid, server_ids, context=None)

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
