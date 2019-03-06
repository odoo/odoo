# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Survey CRM',
    'version': '2.0',
    'category': 'Marketing',
    'complexity': 'easy',
    'description': """
Survey - CRM (bridge module)
=================================================================================
This module adds a Survey mass mailing button inside the more option of lead/customers views
""",
    'depends': ['crm', 'survey'],
    'data': [
        'views/survey_crm_views.xml',
    ],
    'installable': True,
    'auto_install': True
}
