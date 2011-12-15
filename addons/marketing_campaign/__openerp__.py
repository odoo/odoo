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
    "name" : "Marketing Campaigns",
    "version" : "1.1",
    "depends" : ["marketing",
                 "document",
                 "email_template",
                 "decimal_precision"
                ],
    "author" : "OpenERP SA",
    "category": 'Marketing',
    'complexity': "expert",
    "description": """
This module provides leads automation through marketing campaigns (campaigns can in fact be defined on any resource, not just CRM Leads).
=========================================================================================================================================

The campaigns are dynamic and multi-channels. The process is as follows:
    * Design marketing campaigns like workflows, including email templates to send, reports to print and send by email, custom actions, etc.
    * Define input segments that will select the items that should enter the campaign (e.g leads from certain countries, etc.)
    * Run you campaign in simulation mode to test it real-time or accelerated, and fine-tune it
    * You may also start the real campaign in manual mode, where each action requires manual validation
    * Finally launch your campaign live, and watch the statistics as the campaign does everything fully automatically.

While the campaign runs you can of course continue to fine-tune the parameters, input segments, workflow, etc.

Note: If you need demo data, you can install the marketing_campaign_crm_demo module, but this will also install the CRM application as it depends on CRM Leads.
    """,
    'website': 'http://www.openerp.com',
    'init_xml': [],
    'update_xml': [
        'marketing_campaign_view.xml',
        'marketing_campaign_data.xml',
        'marketing_campaign_workflow.xml',
        'res_partner_view.xml',
        'report/campaign_analysis_view.xml',
        "security/marketing_campaign_security.xml",
        "security/ir.model.access.csv"
    ],
    'demo_xml': [
    ],
    'installable': True,
    'active': False,
    'certificate' : '00421723279617928365',
    'images': ['images/campaign.png', 'images/campaigns.jpeg','images/email_account.jpeg','images/email_templates.jpeg','images/segments.jpeg'],
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
