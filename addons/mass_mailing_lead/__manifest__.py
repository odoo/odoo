# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Mass mailing on leads',
    'category': 'Hidden',
    'version': '1.0',
    'description':
        """
Mass mail leads integration
===========================

Bridge module adding UX requirements to ease mass mailing of leads.
Typically, apply mass mailing blacklist on leads. 
        """,
    'depends': ['crm', 'mass_mailing'],
    'data': [
        'views/crm_lead_views.xml'
    ],
    'auto_install': True,
}
