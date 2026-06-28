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
        'data/config_parameter.xml',
        'views/translation_mode_settings.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'test_translation_mode/static/src/**/*',
        ],
        'web.assets_frontend': [
            'test_translation_mode/static/src/**/*',
        ],
        'web.assets_unit_tests': [
            'test_translation_mode/static/tests/**/*',
        ],
    },
    'post_init_hook': 'post_init_hook',
    'uninstall_hook': 'uninstall_hook',
    'author': 'Odoo S.A.',
    'license': 'LGPL-3',
}
