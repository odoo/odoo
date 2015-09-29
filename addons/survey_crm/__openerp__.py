# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.


{
    'name': 'Survey CRM',
    'version': '2.0',
    'category': 'Marketing',
    'complexity': 'easy',
    'website': 'https://www.odoo.com/page/survey',
    'description': """
Survey - CRM (bridge module)
=================================================================================
This module adds a Survey mass mailing button inside the more option of lead/customers views
""",
    'depends': ['crm', 'survey'],
    'data': [
        'crm_view.xml',
    ],
    'installable': True,
    'auto_install': True
}
