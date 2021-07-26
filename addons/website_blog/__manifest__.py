# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Blogs',
    'category': 'Website/Website',
    'sequence': 200,
    'website': 'https://www.odoo.com/page/blog-engine',
    'summary': 'Publish blog posts, announces, news',
    'version': '1.0',
    'description': "",
    'depends': ['website_mail', 'website_partner'],
    'data': [
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
    'qweb': [
    ],
    'installable': True,
    'application': True,
    'license': 'LGPL-3',
}
