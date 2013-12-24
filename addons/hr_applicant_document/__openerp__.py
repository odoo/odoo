# -*- coding: utf-8 -*-

{
    'name': 'Applicant Resumes and Letters',
    'version': '1.0',
    'category': 'Human Resources',
    'sequence': 25,
    'summary': 'Search job applications by Index content.',
    'description': """This module allows you to search job applications by content
    of resumes and letters.""",
    'author': 'OpenERP SA',
    'website': 'http://www.openerp.com',
    'depends': [
        'hr_recruitment',
        'document'
    ],
    'data': [
        'views/hr_applicant.xml'
    ],
    'demo': [
        'demo/hr_applicant.xml'
    ],
    'installable': True,
    'auto_install': True,
    'application': True,
}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
