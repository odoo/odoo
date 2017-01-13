# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Odoo Web Diagram',
    'category': 'Hidden',
    'description': """
Openerp Web Diagram view.
=========================

""",
    'version': '2.0',
    'depends': ['web'],
    'data': [
        'views/web_diagram_templates.xml',
    ],
    'qweb': [
        'static/src/xml/*.xml',
    ],
    'auto_install': True,
}
