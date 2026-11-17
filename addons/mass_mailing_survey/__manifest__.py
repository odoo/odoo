# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Mass Mailing with Surveys',
    'summary': 'Send surveys through mailings and capture respondent\'s details',
    'category': 'Marketing/Email Marketing',
    'depends': [
        'mass_mailing',
        'survey',
    ],
    'data': [
        'views/mailing_mailing_views.xml',
        'views/survey_user_input_views.xml',
    ],
    'assets': {
        'mass_mailing.assets_builder': [
            'mass_mailing_survey/static/src/builder/**/*',
        ],
    },
    'auto_install': True,
    'author': 'Odoo S.A.',
    'license': 'LGPL-3',
}
