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
from itertools import chain
from operator import itemgetter
import netsvc

class base_setup_installer(osv.osv_memory):
    _name = 'base.setup.installer'
    _inherit = 'res.config.installer'

    def _get_charts(self, cr, uid, context=None):
        modules = self.pool.get('ir.module.module')
        ids = modules.search(cr, uid, [('category_id','=','Account Charts'),
                                       ('state','!=','installed')])
        return list(
            sorted(((m.name, m.shortdesc)
                    for m in modules.browse(cr, uid, ids)),
                   key=itemgetter(1)))

    def _if_account(self, cr, uid, ids, context=None):
        chart = self.read(cr, uid, ids, ['charts'],
                          context=context)[0]['charts']
        self.logger.notifyChannel(
            'installer', netsvc.LOG_DEBUG,
            'Addon "account" selected, installing chart of accounts %s'%chart)
        return [chart]

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
                 "generating planings, etc..."),
        'knowledge':fields.boolean('Knowledge Management',
            help="Lets you install addons geared towards sharing knowledge "
                 "with and between your employees."),
        'stock':fields.boolean('Warehouse Management',
            help="Helps you manage your stocks and stocks locations, as well "
                 "as the flow of stock between warehouses."),
        'mrp':fields.boolean('Manufacturing'),
        'account':fields.boolean('Financial & Accounting'),
        'charts':fields.selection(_get_charts, 'Chart of Accounts'),
        'purchase':fields.boolean('Purchase Management'),
        'hr':fields.boolean('Human Resources'),
        'point_of_sale':fields.boolean('Point of Sales'),
        'marketing':fields.boolean('Marketing'),
        'misc_tools':fields.boolean('Miscellaneous Tools'),
        'report_designer':fields.boolean('Advanced Reporting'),
        # Vertical modules
        'profile_association':fields.boolean('Associations'),
        'profile_training':fields.boolean('Training Centers'),
        'profile_auction':fields.boolean('Auction Houses'),
        'profile_bookstore':fields.boolean('Book Stores'),
        }
    _defaults = {
        'crm': True,
        }
base_setup_installer()

