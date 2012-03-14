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

class project_configuration(osv.osv_memory):
    _name = 'project.configuration'
    _inherit = 'res.config.settings'

    _columns = {
        'module_project_mrp': fields.boolean('Allow to create tasks directly from a sale order',
                           help ="""
                           Automatically creates project tasks from procurement lines.
                           It installs the project_mrp module.
                           """),
        'module_pad': fields.boolean("Write project specification on collaborative note pad",
                          help="""Lets the company customize which Pad installation should be used to link to new pads
                            (by default, http://ietherpad.com/).
                          It installs the pad module."""),
        'module_project_timesheet': fields.boolean("Invoice working time on task",
                        help="""This allows you to transfer the entries under tasks defined for Project Management to
                        the timesheet line entries for particular date and particular user  with the effect of creating, editing and deleting either ways.
                        It installs the project_timesheet module."""),
        'module_project_scrum': fields.boolean("Allow to manage your project on agile methodology",
                        help="""This allows to implement all concepts defined by the scrum project management methodology for IT companies.
                                * Project with sprints, product owner, scrum master
                                * Sprints with reviews, daily meetings, feedbacks
                                * Product backlog
                                * Sprint backlog.
                            It installs the project_scrum module."""),
        'module_project_planning' : fields.boolean("Manage planning",
                        help="""This module helps you to manage your plannings.
                            each department manager can know if someone in his team has still unallocated time for a given planning (taking in consideration the validated leaves) or if he still needs to encode tasks.
                        It Installs project_planning  module."""),
        'module_project_long_term': fields.boolean("Manage Long term planning",
                        help="""Long Term Project management module that tracks planning, scheduling, resources allocation.
                        It installs the project_long_term module."""),
        'module_project_issue_sheet': fields.boolean("Track and invoice working time",
                        help="""Allows to the timesheet support for the Issues/Bugs Management in Project.
                        It installs the project_issue_sheet module."""),
        'module_project_issue': fields.boolean("Create issue from an email account",
                        help="""This allows you issues/bugs management in project
                        It installs the project_issue module."""),
        'issue_server' : fields.char('Server Name', size=256),
        'issue_port' : fields.integer('Port'),
        'issue_type': fields.selection([
                   ('pop', 'POP Server'),
                   ('imap', 'IMAP Server'),
                   ('local', 'Local Server'),
               ], 'Server Type'),
        'issue_is_ssl': fields.boolean('SSL/TLS', help="Connections are encrypted with SSL/TLS through a dedicated port (default: IMAPS=993, POP=995)"),
        'issue_user' : fields.char('Username', size=256),
        'issue_password' : fields.char('Password', size=1024),
        'module_crm_claim': fields.boolean("Create claims from an email account",
                        help="""This allows you to track your customers/suppliers claims and grievances.
                        It installs the crm_claim module."""),
        'claim_server' : fields.char('Server Name', size=256),
        'claim_port' : fields.integer('Port'),
        'claim_type': fields.selection([
                   ('pop', 'POP Server'),
                   ('imap', 'IMAP Server'),
                   ('local', 'Local Server'),
               ], 'Server Type'),
        'claim_is_ssl': fields.boolean('SSL/TLS', help="Connections are encrypted with SSL/TLS through a dedicated port (default: IMAPS=993, POP=995)"),
        'claim_user' : fields.char('Username', size=256),
        'claim_password' : fields.char('Password', size=1024),
    }

    _defaults = {
        'issue_type': 'pop',
        'claim_type': 'pop',
    }

    def get_default_email_configurations(self, cr, uid, ids, context=None):
        fetchmail_obj = self.pool.get('fetchmail.server')
        result = {}
        issue_ids = fetchmail_obj.search(cr, uid, [('name','=','Incoming Issues'),('state','!=','done')])
        if issue_ids:
            issue_id = fetchmail_obj.browse(cr, uid, issue_ids[0], context=context)
            result.update({'issue_server': issue_id.server})
            result.update({'issue_port': issue_id.port})
            result.update({'issue_is_ssl': issue_id.is_ssl})
            result.update({'issue_type': issue_id.type})
            result.update({'issue_user': issue_id.user})
            result.update({'issue_password': issue_id.password})

        claim_ids = fetchmail_obj.search(cr, uid, [('name','=','Incoming Claims'),('state','!=','done')])
        if claim_ids:
            claim_id = fetchmail_obj.browse(cr, uid, claim_ids[0], context=context)
            result.update({'claim_server': claim_id.server})
            result.update({'claim_port': claim_id.port})
            result.update({'claim_is_ssl': claim_id.is_ssl})
            result.update({'claim_type': claim_id.type})
            result.update({'claim_user': claim_id.user})
            result.update({'claim_password': claim_id.password})

        return result

    def onchange_server_type(self, cr, uid, ids, server_type=False, ssl=False , type=[]):
        port = 0
        values = {}
        if server_type == 'pop':
            port = ssl and 995 or 110
        elif server_type == 'imap':
            port = ssl and 993 or 143
        else:
            values[type+'_server'] = ''
        values[type+'_port'] = port
        return {'value': values}

    def set_email_configurations(self, cr, uid, ids, context=None):
        model_obj = self.pool.get('ir.model')
        fetchmail_obj = self.pool.get('fetchmail.server')
        ir_values_obj = self.pool.get('ir.values')
        issue_id = model_obj.search(cr, uid, [('model','=','project.issue')])
        claim_id = model_obj.search(cr, uid, [('model','=','crm.claim')])
        vals = self.read(cr, uid, ids[0], [], context=context)
        if vals.get('module_project_issue') and issue_id:
            issue_vals = {
                    'name': 'Incoming Issues',
                    'object_id': issue_id[0],
                    'server': vals.get('issue_server'),
                    'port': vals.get('issue_port'),
                    'is_ssl': vals.get('issue_is_ssl'),
                    'type': vals.get('issue_type'),
                    'user': vals.get('issue_user'),
                    'password': vals.get('issue_password')
            }
            server_ids = fetchmail_obj.search(cr, uid, [('name','=','Incoming Issues'),('state','!=','done')])
            if not server_ids:
                server_ids = [fetchmail_obj.create(cr, uid, issue_vals, context=context)]
            else:
                server_ids = fetchmail_obj.search(cr, uid, [('name','=','Incoming Issues')], context=context)
                fetchmail_obj.write(cr, uid, server_ids, issue_vals, context=context)
            fetchmail_obj.button_confirm_login(cr, uid, server_ids, context=None)

        else:
            server_ids = fetchmail_obj.search(cr, uid, [('name','=','Incoming Issues'),('state','=','done')])
            fetchmail_obj.set_draft(cr, uid, server_ids, context=None)

        if vals.get('module_crm_claim') and claim_id:
            claim_vals = {
                    'name': 'Incoming Claims',
                    'object_id': claim_id[0],
                    'server': vals.get('claim_server'),
                    'port': vals.get('claim_port'),
                    'is_ssl': vals.get('claim_is_ssl'),
                    'type': vals.get('claim_type'),
                    'user': vals.get('claim_user'),
                    'password': vals.get('claim_password')
            }
            server_ids = fetchmail_obj.search(cr, uid, [('name','=','Incoming Claims'),('state','!=','done')])
            if not server_ids:
                server_ids = [fetchmail_obj.create(cr, uid, claim_vals, context=context)]
            else:
                server_ids = fetchmail_obj.search(cr, uid, [('name','=','Incoming Claims')], context=context)
                fetchmail_obj.write(cr, uid, server_ids, claim_vals, context=context)
            fetchmail_obj.button_confirm_login(cr, uid, server_ids, context=None)

        else:
            server_ids = fetchmail_obj.search(cr, uid, [('name','=','Incoming Claims'),('state','=','done')])
            fetchmail_obj.set_draft(cr, uid, server_ids, context=None)

project_configuration()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: