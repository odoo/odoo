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


{
    'category': 'Customer Relationship Management', 
    'name': 'Helpdesk',
    'version': '1.0',
    'description': """
Helpdesk Management.
====================

Like records and processing of claims, Helpdesk and Support are good tools
to trace your interventions. This menu is more adapted to oral communication,
which is not necessarily related to a claim. Select a customer, add notes
and categorize your interventions with a channel and a priority level.
    """,
    'author': 'OpenERP SA',
    'website': 'http://www.openerp.com',
    'depends': ['crm'],
    'data': [
         'crm_helpdesk_data.xml',
    ],
    'data': [
        'crm_helpdesk_view.xml',
        'crm_helpdesk_menu.xml',
        'security/ir.model.access.csv',
        'report/crm_helpdesk_report_view.xml',
    ],
    'demo': [
        'crm_helpdesk_demo.xml',
    ],
    'test': ['test/process/help-desk.yml'],
    'installable': True,
    'auto_install': False,
    'certificate' : '00830691522781519309',
    'images': ['images/helpdesk_analysis.jpeg','images/helpdesk_categories.jpeg','images/helpdesk_requests.jpeg'],
}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
