# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Portal Rating',
    'category': 'Services',
    'description': """
Bridge module adding rating capabilities on portal. It includes notably
inclusion of rating directly within the customer portal discuss widget.
        """,
    'depends': [
        'portal',
        'rating',
    ],
    'data': [
        'views/rating_rating_views.xml',
        'views/portal_templates.xml',
        'views/rating_templates.xml',
    ],
    'auto_install': True,
    'assets': {
        'web.assets_frontend': [
            'portal_rating/static/src/scss/portal_rating.scss',
            'portal_rating/static/src/xml/portal_chatter.xml',
            'portal_rating/static/src/interactions/**/*',
            'portal_rating/static/src/xml/portal_rating_composer.xml',
            'portal_rating/static/src/xml/portal_tools.xml',
            # needed for fields definition on lazy loading the portal chatter
            'mail/static/src/utils/common/local_storage.js',
            'mail/static/src/utils/common/misc.js',
            'mail/static/src/model/**.*',
            'rating/static/src/core/common/rating_model.js',
            'portal_rating/static/src/core/common/rating_model_patch.js',
        ],
        'web.assets_unit_tests_setup': [
            'portal_rating/static/src/interactions/**/*',
            'portal_rating/static/src/xml/**/*',
        ],
        'portal.assets_chatter': [
            'portal_rating/static/src/chatter/portal/**/*',
        ],
        'portal.assets_chatter_style': [
            'portal_rating/static/src/scss/portal_rating.scss',
        ]
    },
    'author': 'Odoo S.A.',
    'license': 'LGPL-3',
}
