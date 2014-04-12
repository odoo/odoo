# -*- coding: utf-8 -*-

{
    'name': 'Mass Mailing with Recruitment',
    'version': '1.0',
    'depends': ['mass_mailing', 'hr_recruitment'],
    'author': 'OpenERP SA',
    'category': 'Hidden/Dependency',
    'description': """
Bridge module between Mass Mailing and HR Recruitment
    """,
    'website': 'http://www.openerp.com',
    'data': [
        'views/hr_applicant.xml',
    ],
    'demo': [],
    'installable': True,
    'auto_install': True,
}
