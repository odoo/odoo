# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution	
#    Copyright (C) 2004-2008 Tiny SPRL (<http://tiny.be>). All Rights Reserved
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
    "name" : "Customer Relationship Management",
    "version" : "1.0",
    "author" : "Tiny",
    "website" : "http://tinyerp.com/module_crm.html",
    "category" : "Generic Modules/CRM & SRM",
    "description": """
The Open ERP case and request tracker enables a group of
people to intelligently and efficiently manage tasks, issues,
and requests. It manages key tasks such as communication, 
identification, prioritization, assignment, resolution and notification.

This module provide screens like: jobs hiring process, leads, business
opportunities, fund raising trackings, support & helpdesk, calendar of
meetings, eso.
""",
    "depends" : ["crm","report_crm", "process"],
    "init_xml" : [
        "crm_configuration_wizard.xml",
        "crm_config_view.xml",
        "crm_bugs_view.xml",
        "crm_jobs_view.xml",
        "crm_lead_view.xml",
        "crm_meeting_view.xml",
        "crm_opportunity_view.xml",
        "crm_fund_view.xml",
        "crm_claims_view.xml",
        "crm_phonecall_view.xml",
        "crm_report_view.xml"
    ],
    "demo_xml" : [
#        "crm_bugs_demo.xml",
#        "crm_fund_demo.xml",
#        "crm_jobs_demo.xml",
#        "crm_meeting_demo.xml",
#        "crm_lead_demo.xml",
#        "crm_opportunity_demo.xml",
#        "crm_claims_demo.xml", 
#        "crm_phonecall_demo.xml", 
   ],
   "update_xml" : [
#         "crm_bugs_data.xml",
#         "crm_fund_data.xml",
#         "crm_jobs_data.xml",
#         "crm_meeting_data.xml",
#         "crm_lead_data.xml",
#         "crm_bugs_menu.xml",
#         "crm_fund_menu.xml",
#         "crm_jobs_menu.xml",
#         "crm_helpdesk_menu.xml",
#         "crm_lead_menu.xml",
#         "crm_meeting_menu.xml",
#         "crm_opportunity_data.xml",
#         "crm_opportunity_menu.xml",
#         "crm_claims_data.xml",
#         "crm_claims_menu.xml",
#         "crm_phonecall_data.xml",
#         "crm_phonecall_menu.xml",
         "security/ir.model.access.csv",
         "process/crm_configuration_process.xml",
    ],
    "active": False,
    "installable": True
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

