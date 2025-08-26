# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Blog',
    'category': 'Website/Website',
    'sequence': 200,
    'website': 'https://www.odoo.com/app/blog',
    'summary': 'Publish blog posts, announces, news',
    'version': '1.1',
    'depends': ['website_mail', 'website_partner', 'html_builder'],
    'data': [
        'data/mail_message_subtype_data.xml',
        'data/mail_templates.xml',
        'data/website_blog_data.xml',
        'data/blog_snippet_template_data.xml',
        'data/website_blog_tour.xml',
        'views/website_blog_views.xml',
        'views/website_blog_components.xml',
        'views/website_blog_posts_loop.xml',
        'views/website_blog_templates.xml',
        'views/snippets/snippets.xml',
        'views/snippets/s_blog_posts.xml',
        'views/snippets/s_dynamic_snippet_blog_posts_preview_data.xml',
        'views/website_pages_views.xml',
        'views/blog_post_add.xml',
        'security/ir.model.access.csv',
        'security/website_blog_security.xml',
    ],
    'demo': [
        'data/website_blog_demo.xml'
    ],
    'installable': True,
    'assets': {
        'web.assets_backend': [
            'website_blog/static/src/tours/website_blog.js',
        ],
        'web.assets_tests': [
            'website_blog/static/tests/tours/**/*',
        ],
        'web.assets_unit_tests': [
            'website_blog/static/tests/interactions/**/*',
            'website_blog/static/tests/website_builder/**/*',
        ],
        'web.assets_unit_tests_setup': [
            'website_blog/static/src/interactions/**/*.js',
            'website_blog/static/src/snippets/**/*.js',
        ],
        'web.assets_frontend': [
            'website_blog/static/src/interactions/**/*',
            'website_blog/static/src/scss/website_blog.scss',
            'website_blog/static/src/snippets/**/*.js',
        ],
        'website.assets_editor': [
            'website_blog/static/src/js/systray_items/*.js',
        ],
        'website.website_builder_assets': [
            'website_blog/static/src/website_builder/**/*',
        ],
    },
    'author': 'Odoo S.A.',
    'license': 'LGPL-3',
}
