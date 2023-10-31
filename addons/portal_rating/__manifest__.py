# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Portal Rating',
    'category': 'Hidden',
    'version': '1.0',
    'description': """
Bridge module adding rating capabilities on portal. It includes notably
inclusion of rating directly within the customer portal discuss widget.
        """,
    'depends': [
        'portal',
        'rating',
    ],
    'data': [
        'views/rating_views.xml',
        'views/portal_templates.xml',
        'views/rating_templates.xml',
    ],
    'auto_install': True,
    'assets': {
        'web.assets_frontend': [
            'portal_rating/static/src/scss/portal_rating.scss',
            'portal_rating/static/src/js/portal_chatter.js',
            'portal_rating/static/src/js/portal_composer.js',
            'portal_rating/static/src/js/portal_rating_composer.js',
        ],
    },
    'license': 'LGPL-3',
}
