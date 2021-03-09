# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Blogs',
    'category': 'Website/Website',
    'sequence': 200,
    'website': 'https://www.odoo.com/page/blog-engine',
    'summary': 'Publish blog posts, announces, news',
    'version': '1.1',
    'description': "",
    'depends': ['website_mail', 'website_partner'],
    'data': [
        'data/ir_asset.xml',
        'data/mail_data.xml',
        'data/mail_templates.xml',
        'data/website_blog_data.xml',
        'views/website_blog_views.xml',
        'views/website_blog_components.xml',
        'views/website_blog_posts_loop.xml',
        'views/website_blog_templates.xml',
        'views/snippets/snippets.xml',
        'views/snippets/s_latest_posts.xml',
        'security/ir.model.access.csv',
        'security/website_blog_security.xml',
    ],
    'demo': [
        'data/website_blog_demo.xml'
    ],
    'test': [
    ],
    'installable': True,
    'application': True,
    'assets': {
        'website.assets_wysiwyg': [
            # inside .
            'website_blog/static/src/snippets/s_latest_posts/options.js',
        ],
        'website.assets_editor': [
            # inside .
            'website_blog/static/src/js/website_blog.editor.js',
            # inside .
            'website_blog/static/src/js/tours/website_blog.js',
        ],
        'web.assets_frontend': [
            # inside .
            'website_blog/static/src/scss/website_blog.scss',
            # inside .
            'website_blog/static/src/js/contentshare.js',
            # inside .
            'website_blog/static/src/js/website_blog.js',
            # after //link[last()]
            'website_blog/static/src/snippets/s_latest_posts/001.scss',
            # after //script[last()]
            'website_blog/static/src/snippets/s_latest_posts/000.js',
        ],
        'web.assets_qweb': [

        ],
    }
}
