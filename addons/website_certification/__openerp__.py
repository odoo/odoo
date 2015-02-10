# -*- coding: utf-8 -*-
{
    'name': 'Certified People',
    'category': 'Website',
    'website': 'https://www.odoo.com/page/website-builder',
    'summary': 'Display your network of certified people on your website',
    'version': '1.0',
    'author': 'Odoo S.A.',
    'depends': ['marketing', 'website'],
    'description': """
    Display your network of certified people on your website
    """,
    'data': [
        'security/ir.model.access.csv',
        'views/certification_views.xml',
        'views/certification_templates.xml',
    ],
    'installable': True,
}
