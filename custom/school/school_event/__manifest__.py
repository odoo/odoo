# -*- coding: utf-8 -*-
# See LICENSE file for full copyright and licensing details.

{
    'name': 'School Event Management',
    'version': "10.0.1.0.3",
    'author': '''Francis Bangura. <francisbnagura@gmail.com>''',
    'website': 'https://www.byteltd.com/',
    'category': 'School Management',
    'license': "AGPL-3",
    'complexity': 'easy',
    'summary': 'A Module For Event Management In School',
    'depends': ['school'],
    'data': ['security/event_security.xml',
             'security/ir.model.access.csv',
             'views/event_view.xml',
             'views/participants.xml',
             'views/report_view.xml'],
    'demo': ['demo/event_demo.xml'],
    'installable': False,
    'application': True
}
