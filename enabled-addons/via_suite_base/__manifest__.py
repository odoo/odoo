# -*- coding: utf-8 -*-
{
    'name': 'ViaSuite Base',
    'version': '19.0.1.0.0',
    'category': 'Hidden',
    'summary': 'Core customizations for ViaSuite - ViaFronteira retail solution',
    'description': """
        ViaSuite Base Module
        ====================
        
        Core module providing base customizations for ViaSuite:
        
        Features:
        ---------
        * Keycloak SSO integration (multi-tenant)
        * Multi-language support (pt_BR, es_PY, en_US, ar_SA, zh_CN)
        
        This module is auto-installed and provides the foundation for all
        ViaSuite tenants.
    """,
    'author': 'ViaFronteira, LLC',
    'website': 'https://www.viafronteira.com',
    'license': 'LGPL-3',
    'depends': [
        'base',
        'web',
        'auth_oauth'
    ],
    'data': [
        'data/auth_oauth_provider.xml',
        'views/auth_templates.xml',
    ],
    # 'assets': {
    #     'web.assets_backend': [
    #         'via_suite_base/static/src/scss/viasuite_theme.scss',
    #     ],
    #     'web.assets_frontend': [
    #         'via_suite_base/static/src/scss/viasuite_theme.scss',
    #     ],
    # },
    # 'external_dependencies': {
    #     'python': [
    #         'sentry_sdk',
    #     ],
    # },
    'post_init_hook': 'post_init_hook',
    'auto_install': False,
    'application': False,
    'installable': True,
}