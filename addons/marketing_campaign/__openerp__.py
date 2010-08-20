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
    "name" : "marketing_campaign",
    "version" : "1.1",
    "depends" : ["marketing",
                 "document",
                 "email_template"
                ],
    "author" : "OpenERP SA",
    "category": 'Generic Modules/Marketing',
    "description": """
Allows you to setup leads automation through marketing campaigns. The campaigns
are dynamic and multi-channels. The process:
* Design marketing campaigns that incluces mail templates, reports to print,
  miscelleanous actions, etc.
* Define segments that are selections of target people
* Launch your campaign to automate communications.

If you need demo data, you can install the module marketing_campaign_crm_demo.
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
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
