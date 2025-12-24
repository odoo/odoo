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
        * AWS S3 storage for attachments
        * Amazon SES email configuration
        * Structured logging with JSON output
        * Sentry error tracking integration
        * Custom branding (ViaSuite/ViaFronteira, LLC)
        * Multi-language support (pt_BR, es_PY, en_US, ar_SA, zh_CN)
        * Automated cleanup jobs for sessions, logs, and attachments
        * Login/logout audit logging
        * Custom session timeout (24h for PDV operations)
        * PWA support with custom favicon and manifest
        
        This module is auto-installed and provides the foundation for all
        ViaSuite tenants.
    """,
    'author': 'ViaFronteira, LLC',
    'website': 'https://www.viafronteira.com',
    'license': 'LGPL-3',
    'depends': [
        'base',
        'web',
        'mail',
        'auth_oauth'
    ],
    'data': [
        # Security
        'security/via_suite_login_audit_security.xml',
        'security/ir.model.access.csv',

        # Data
        'data/ir_config_parameter.xml',
        'data/mail_server.xml',
        'data/mail_template.xml',
        'data/auth_oauth_provider.xml',
        'data/ir_cron.xml',

        # Views
        'views/webclient_templates.xml',
        'views/login_templates.xml',
        'views/res_config_settings_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'via_suite_base/static/src/scss/viasuite_theme.scss',
        ],
        'web.assets_frontend': [
            'via_suite_base/static/src/scss/viasuite_theme.scss',
        ],
    },
    'external_dependencies': {
        'python': [
            'structlog',
            'python-json-logger',
            'sentry_sdk',
            'boto3',
            's3fs',
            'fsspec',
        ],
    },
    'post_init_hook': 'post_init_hook',
    'auto_install': True,
    'application': False,
    'installable': True,
}