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


{
    'name': 'Customer Relationship Management',
    'version': '1.0',
    'category': 'Generic Modules/CRM & SRM',
    'description': """
The Open ERP case and request tracker enables a group of
people to intelligently and efficiently manage tasks, issues,
and requests. It manages key tasks such as communication, 
identification, prioritization, assignment, resolution and notification.

This module provide screens like: jobs hiring process, prospects, business
opportunities, fund raising tracking, support & helpdesk, calendar of
meetings, eso.
""",
    'author': 'Tiny',
    'website': 'http://www.openerp.com',
    'depends': ['crm', 'report_crm', 'process'],
    'init_xml': [
        'crm_configuration_wizard.xml',
        'crm_config_view.xml',
        'crm_bugs_view.xml',
        'crm_jobs_view.xml',
        'crm_lead_view.xml',
        'crm_meeting_view.xml',
        'crm_opportunity_view.xml',
        'crm_fund_view.xml',
        'crm_claims_view.xml',
        'crm_phonecall_view.xml',
        'crm_report_view.xml'
    ],
    'update_xml': ['security/ir.model.access.csv', 'process/crm_configuration_process.xml'],
    'demo_xml': [],
    'installable': True,
    'active': False,
    'certificate': '0080531386589',
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
