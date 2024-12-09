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
        'views/rating_rating_views.xml',
        'views/portal_templates.xml',
        'views/rating_templates.xml',
    ],
    'auto_install': True,
    'assets': {
        'web.assets_frontend': [
            'portal_rating/static/src/scss/portal_rating.scss',
            'portal_rating/static/src/xml/portal_tools.xml',
            'portal_rating/static/src/chatter/boot/boot_service_patch.js',
            # needed for fields definition on lazy loading the portal chatter
            'mail/static/src/utils/common/misc.js',
            'mail/static/src/model/**.js',
            'mail/static/src/core/common/record.js',
            'rating/static/src/core/common/rating_model.js',
            'portal_rating/static/src/core/common/rating_model_patch.js',
        ],
        'portal.assets_chatter': [
            'portal_rating/static/src/chatter/frontend/**/*',
        ],
        'web_editor.backend_assets_wysiwyg': [
            'portal_rating/static/src/chatter/web/wysiwyg.js',
        ],
        'portal.assets_chatter_style': [
            'portal_rating/static/src/chatter/frontend/**/*.scss',
            'portal_rating/static/src/scss/portal_rating.scss',
            'web_editor/static/src/scss/web_editor.common.scss',
        ]
    },
    'license': 'LGPL-3',
}
