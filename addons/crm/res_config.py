# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Business Applications
#    Copyright (C) 2004-2012 OpenERP S.A. (<http://openerp.com>).
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
    _name = 'sale.config.settings'
    _inherit = ['sale.config.settings', 'fetchmail.config.settings']

    _columns = {
        'fetchmail_lead': fields.boolean("create leads from incoming mails",
            fetchmail_model='crm.lead', fetchmail_name='Incoming Leads',
            help="""Allows you to configure your incoming mail server, and create leads from incoming emails."""),
        'module_crm_caldav': fields.boolean("applications with Caldav protocol",
            help="""Use protocol caldav to synchronize meetings with other calendar applications (like Sunbird).
                This installs the module crm_caldav."""),
        'module_import_sugarcrm': fields.boolean("SugarCRM",
            help="""Import SugarCRM leads, opportunities, users, accounts, contacts, employees, meetings, phonecalls, emails, project and project tasks data.
                This installs the module import_sugarcrm."""),
        'module_import_google': fields.boolean("Google (Contacts and Calendar)",
            help="""Import google contact in partner address and add google calendar events details in Meeting.
                This installs the module import_google."""),
        'module_google_map': fields.boolean("add google maps on customer",
            help="""Locate customers on Google Map.
                This installs the module google_map."""),
        'group_fund_raising': fields.boolean("Manage Fund Raising",
            implied_group='crm.group_fund_raising',
            help="""Allows you to trace and manage your activities for fund raising."""),
    }

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
