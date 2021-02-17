# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Email Attachment',
    'version': '14.0.1.0.0',
    'summary': '--------------------',
    'sequence': 12,
    'description': """eMail""",
    'category': '',
    'depends': [
            'base',
            'contacts',
            'qweb_report',
    ],
    'website': 'https://www.xyz.com',
    'data': [
        # 'wizard/purchase_report_email.xml',
        'data/product_movement_report_email_template.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
}
# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

