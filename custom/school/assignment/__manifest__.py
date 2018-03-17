# -*- coding: utf-8 -*-
# See LICENSE file for full copyright and licensing details.

{
    'name': 'Assignment Management',
    'version': "10.0.1.0.4",
    'author': '''Francis Bangura. <francisbnagura@gmail.com>''',
    'website': 'https://www.byteltd.com/',
    'license': "AGPL-3",
    'category': 'School Management',
    'summary': 'A Module For Assignment Management In School',
    'complexity': 'easy',
    'depends': ['school'],
    'data': ['security/assignment_security.xml',
             'wizard/reason_wiz_view.xml',
             'views/homework_view.xml',
             'security/ir.model.access.csv'
             ],
    'demo': [
        #'demo/assignment_demo.xml'
    ],
    'installable': True,
    'application': True,
    'auto_install': False
}
