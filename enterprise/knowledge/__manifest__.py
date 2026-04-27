# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Knowledge',
    'summary': 'Centralize, manage, share and grow your knowledge library',
    'description': 'Centralize, manage, share and grow your knowledge library',
    'category': 'Productivity/Knowledge',
    'version': '1.0',
    'depends': [
        'web',
        'web_editor',  # still needed for backend history functions
        'digest',
        'html_editor',
        'mail',
        'portal',
        'web_unsplash',
        'web_hierarchy',
    ],
    'data': [
        'data/article_templates.xml',
        'data/digest_data.xml',
        'data/ir_config_parameter_data.xml',
        'data/ir_attachment_data.xml',
        'data/knowledge_cover_data.xml',
        'data/knowledge_article_template_category_data.xml',
        'data/knowledge_article_template_data.xml',
        'data/knowledge_article_stage_data.xml',
        'data/ir_actions_data.xml',
        'data/mail_templates.xml',
        'data/mail_templates_email_layouts.xml',
        'wizard/knowledge_invite_views.xml',
        'views/knowledge_article_views.xml',
        'views/knowledge_article_favorite_views.xml',
        'views/knowledge_article_member_views.xml',
        'views/knowledge_article_stage_views.xml',
        'views/knowledge_article_template_category_views.xml',
        'views/knowledge_templates_portal.xml',
        'views/knowledge_menus.xml',
        'views/portal_templates.xml',
        'security/ir.model.access.csv',
        'security/ir_rule.xml',
    ],
    'installable': True,
    'application': True,
    'license': 'OEEL-1',
    'pre_init_hook': 'pre_init_knowledge',
    'post_init_hook': '_init_private_article_per_user',
    'uninstall_hook': '_uninstall_knowledge',
    'assets': {
        'web.assets_backend': [
            'knowledge/static/src/scss/knowledge_common.scss',
            'knowledge/static/src/scss/knowledge_views.scss',
            'knowledge/static/src/scss/knowledge_editor.scss',
            ('after', 'web/static/src/views/form/form_controller.xml', 'knowledge/static/src/xml/form_controller.xml'),
            'knowledge/static/src/xml/**/*',
            'knowledge/static/src/components/**/*',
            'knowledge/static/src/editor/**/*',
            'knowledge/static/src/comments/**/*',
            'knowledge/static/src/mail/**/*',
            'knowledge/static/src/search_model/**/*',
            ('after', 'web/static/src/views/form/form_controller.js', 'knowledge/static/src/web/form_controller_patch.js'),
            'knowledge/static/src/web/**/*',
            'knowledge/static/src/js/knowledge_controller.js',
            'knowledge/static/src/js/knowledge_utils.js',
            'knowledge/static/src/js/knowledge_renderers.js',
            'knowledge/static/src/js/knowledge_views.js',
            'knowledge/static/src/webclient/**/*',
            'knowledge/static/src/views/**/*',
            ('remove', 'knowledge/static/src/views/hierarchy/**'),
            'knowledge/static/src/services/**/*',
            'knowledge/static/src/macros/**/*',
        ],
        'web.assets_backend_lazy': [
            'knowledge/static/src/views/hierarchy/**',
        ],
        'web.assets_backend_lazy_dark': [
            'knowledge/static/src/scss/knowledge_views.dark.scss',
        ],
        "web.assets_web_dark": [
            'knowledge/static/src/scss/knowledge_views.dark.scss',
        ],
        'web.assets_frontend': [
            'knowledge/static/src/scss/knowledge_common.scss',
            'knowledge/static/src/js/knowledge_utils.js',
        ],
        'web.assets_unit_tests': [
            'knowledge/static/tests/**/*',
            ('remove', 'knowledge/static/tests/legacy/**/*'),
            ('remove', 'knowledge/static/tests/tours/**/*'),
        ],
        'web.assets_tests': [
            'knowledge/static/tests/tours/**/*',
        ],
        # 'web.qunit_suite_tests': [
        #     # 'knowledge/static/tests/legacy/**/*',  # TODO: conversion
        # ],
        'web.tests_assets': [
            'knowledge/static/tests/legacy/mock_services.js',
        ],
        'knowledge.webclient': [
            ('include', 'web.assets_backend'),
            # knowledge webclient overrides
            'knowledge/static/src/portal_webclient/**/*',
            'web/static/src/start.js',
        ],
        'web.assets_web_print': [
            ('include', 'knowledge.assets_knowledge_print'),
        ],
        'knowledge.assets_knowledge_print': [
            'knowledge/static/src/scss/knowledge_print.scss',
        ],
    },
}
