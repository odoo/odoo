# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Translation Mode',
    'category': 'Hidden',
    'summary': 'In-context and interactive translation mode to streamline the module translation process using Weblate',
    'description': """
The translation mode is available when several languages are installed. Select the language to translate,
enable the interactive translation mode from the command palette then browse the screens to translate.
By default, the translate feature redirects to the Odoo official translation project powered by Weblate.
In the settings, a custom Weblate project can be targeted.""",
    'depends': ['web'],
    'data': [
        'security/ir.model.access.csv',
        'data/config_parameter.xml',
        'views/translation_mode_settings.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'translation_mode/static/src/**/*',
        ],
        'web.assets_frontend': [
            'translation_mode/static/src/**/*',
        ],
        'web.assets_unit_tests': [
            'translation_mode/static/tests/**/*',
        ],
    },
    'pre_init_hook': 'pre_init_hook',
    'post_init_hook': 'post_init_hook',
    'author': 'Odoo S.A.',
    'license': 'LGPL-3',
}
