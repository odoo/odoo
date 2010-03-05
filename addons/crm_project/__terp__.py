# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>). All Rights Reserved
#    $Id$
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################


{
    'name': 'Bug Reporting in Project Management',
    'version': '1.0',
    'category': 'Generic Modules/CRM & SRM',
    'description': """
        This module provide  Store the project  bugs with  cases
    """,
    'author': 'Tiny',
    'website': 'http://www.openerp.com',
    'depends': ['crm','project'],
    'init_xml': [
        'crm_bugs_data.xml'
    ],
    'update_xml': [
        'crm_bug_wizard.xml',
        'crm_bugs_view.xml',
        'crm_bugs_menu.xml',        
        'crm_feature_menu.xml',
        'crm_report_project_bug_view.xml',
        'security/crm_project_security.xml',
        'security/ir.model.access.csv',
     ],
    'demo_xml': ['crm_bugs_demo.xml'],
    'installable': True,
    'active': False,
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
