# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Blog',
    'category': 'Website/Website',
    'sequence': 200,
    'website': 'https://www.odoo.com/app/blog',
    'summary': 'Publish blog posts, announces, news',
    'version': '1.1',
    'depends': ['website_mail', 'website_partner'],
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
        'website.assets_wysiwyg': [
            'website_blog/static/src/js/options.js',
            'website_blog/static/src/snippets/s_blog_posts/options.js',
        ],
        'website.assets_editor': [
            'website_blog/static/src/js/tours/website_blog.js',
            'website_blog/static/src/js/systray_items/*.js',
        ],
        'website.backend_assets_all_wysiwyg': [
            'website_blog/static/src/js/wysiwyg_adapter.js',
        ],
        'web.assets_tests': [
            'website_blog/static/tests/**/*',
        ],
        'web.assets_frontend': [
            'website_blog/static/src/scss/website_blog.scss',
            'website_blog/static/src/js/website_blog.js',
        ],
    },
    'license': 'LGPL-3',
}
