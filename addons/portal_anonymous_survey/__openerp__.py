{
    'name': 'Anonymous portal for Survey',
    'version': '0.1',
    'category': 'Tools',
    'complexity': 'easy',
    'description': """
This module adds authenticate options to survey and portal anonymous are installed.
===================================================================================
    """,
    'author': 'OpenERP SA',
    'depends': ['survey','portal_anonymous'],
    'data': [
        'portal_anonymous_survey_view.xml',
    ],
    'installable': True,
    'auto_install': True,
    'category': 'Hidden',
}