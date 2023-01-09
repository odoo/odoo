# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Resellers',
    'category': 'Website/Website',
    'summary': 'Publish your resellers/partners and forward leads to them',
    'version': '1.2',
    'description': """
This module allows to publish your resellers/partners on your website and to forward incoming leads/opportunities to them.


**Publish a partner**

To publish a partner, set a *Level* in their contact form (in the Partner Assignment section) and click the *Publish* button.

**Forward leads**

Forwarding leads can be done for one or several leads at a time. The action is available in the *Assigned Partner* section of the lead/opportunity form view and in the *Action* menu of the list view.

The automatic assignment is figured from the weight of partner levels and the geolocalization. Partners get leads that are located around them.

    """,
    'depends': ['base_geolocalize', 'crm', 'account',
                'website_partner', 'website_google_map', 'portal'],
    'data': [
        'data/crm_lead_merge_template.xml',
        'data/crm_tag_data.xml',
        'data/mail_template_data.xml',
        'data/res_partner_activation_data.xml',
        'data/res_partner_grade_data.xml',
        'security/ir.model.access.csv',
        'security/ir_rule.xml',
        'wizard/crm_forward_to_partner_view.xml',
        'views/res_partner_views.xml',
        'views/res_partner_activation_views.xml',
        'views/res_partner_grade_views.xml',
        'views/crm_lead_views.xml',
        'views/website_crm_partner_assign_templates.xml',
        'views/partner_assign_menus.xml',
        'report/crm_partner_report_view.xml',
        'views/snippets.xml',
    ],
    'demo': [
        'data/res_partner_demo.xml',
        'data/crm_lead_demo.xml',
        'data/res_partner_grade_demo.xml',
    ],
    'installable': True,
    'assets': {
        'web.assets_frontend': [
            'website_crm_partner_assign/static/src/**/*',
        ],
    },
    'license': 'LGPL-3',
}
