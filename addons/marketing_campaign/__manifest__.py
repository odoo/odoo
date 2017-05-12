# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Marketing Campaigns',
    'version': '1.1',
    'depends': ['document', 'mail', 'decimal_precision'],
    'category': 'Marketing',
    'description': """
This module provides leads automation through marketing campaigns (campaigns can in fact be defined on any resource, not just CRM Leads).
=========================================================================================================================================

The campaigns are dynamic and multi-channels. The process is as follows:
------------------------------------------------------------------------
    * Design marketing campaigns like workflows, including email templates to
      send, reports to print and send by email, custom actions
    * Define input segments that will select the items that should enter the
      campaign (e.g leads from certain countries.)
    * Run your campaign in simulation mode to test it real-time or accelerated,
      and fine-tune it
    * You may also start the real campaign in manual mode, where each action
      requires manual validation
    * Finally launch your campaign live, and watch the statistics as the
      campaign does everything fully automatically.

While the campaign runs you can of course continue to fine-tune the parameters,
input segments, workflow.

**Note:** If you need demo data, you can install the marketing_campaign_crm_demo
      module, but this will also install the CRM application as it depends on
      CRM Leads.
    """,
    'website': 'https://www.odoo.com/page/lead-automation',
    'data': [
        'security/marketing_campaign_security.xml',
        'security/ir.model.access.csv',
        'views/marketing_campaign_views.xml',
        'data/marketing_campaign_data.xml',
        'report/campaign_analysis_view.xml',
    ],
    'demo': ['data/marketing_campaign_demo.xml'],
}
