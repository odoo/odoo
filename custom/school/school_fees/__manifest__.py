# -*- coding: utf-8 -*-
# See LICENSE file for full copyright and licensing details.

{
    'name': 'Fees Management',
    'version': "10.0.1.0.4",
    'author': '''Francis Bangura. <francisbnagura@gmail.com>''',
    'website': 'https://www.byteltd.com/',
    'category': 'School Management',
    'license': "AGPL-3",
    'complexity': 'easy',
    'summary': 'A Module For Fees Management In School',
    'depends': ['school'],
    'data': [
             'security/ir.model.access.csv',
             'security/security_fees.xml',
             'views/school_fees_view.xml',
             'views/school_fees_sequence.xml',
             #'views/student_payslip.xml',
             'views/student_fees_register.xml',
             'views/report_view.xml'
         ],
    'demo': [
        #'demo/school_fees_demo.xml'
    ],
    'installable': True,
    'application': True
}
