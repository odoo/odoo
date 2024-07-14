# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Knowledge Website',
    'summary': 'Publish your articles',
    'version': '1.0',
    'depends': ['knowledge', 'website'],
    'data': [
        'security/ir.model.access.csv',
        'security/ir_rule.xml',
        'views/knowledge_views.xml',
        'views/knowledge_templates_public.xml',
    ],
    'installable': True,
    'auto_install': True,
    'license': 'OEEL-1',
    'assets': {
        'web.assets_backend': [
            'website_knowledge/static/src/client_actions/website_preview/website_preview.js',
            'website_knowledge/static/src/js/components/**/*.xml',
            'website_knowledge/static/src/js/components/**/*.js',
            'website_knowledge/static/src/components/**/*',
        ],
        'web.assets_frontend': [
            'website_knowledge/static/src/js/knowledge_public.js',
            'website_knowledge/static/src/scss/knowledge_public.scss',
            'website_knowledge/static/src/xml/knowledge_public.xml',
        ],
        'web.assets_tests': [
            'website_knowledge/static/tests/tours/**/*',
        ],
    },
}
