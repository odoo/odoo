# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Mass mailing on Lead/Opportunity',
    'category': 'Hidden',
    'version': '1.0',
    'description':
        """
Mass mail list using lead/opportunity model
=========================

Bridge module adding UX requirements to ease mass mailing of crm.lead.
        """,
    'depends': ['crm', 'mass_mailing'],
    'data': [
        'views/mass_mailing_crm_views.xml'
    ],
    'auto_install': True,
}
