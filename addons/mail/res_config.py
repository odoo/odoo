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

class plugin_configuration(osv.osv_memory):
    _inherit = 'sale.config.settings'
    
    _columns = {
        'module_plugin_thunderbird': fields.boolean('Thunderbird plugin',
            help="""The plugin allows you archive email and its attachments to the selected
                OpenERP objects. You can select a partner, a task, a project, an analytical
                account, or any other object and attach the selected mail as a .eml file in
                the attachment of a selected record. You can create documents for CRM Lead,
                HR Applicant and Project Issue from the selected emails.
                This installs the module plugin_thunderbird."""),
        'module_plugin_outlook': fields.boolean('Outlook plugin',
            help="""The Outlook plugin allows you to select an object that you would like to add
                to your email and its attachments from MS Outlook. You can select a partner, a task,
                a project, an analytical account, or any other object and archive a selected
                email into an OpenERP mail message with attachments.
                This installs the module plugin_outlook."""),
    }

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
