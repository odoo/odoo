{
    'name': 'Odx Backend Theme (community edition)',
    'version': '19.0.1.0.0',
    'summary': 'Modern backend UI theme for Odoo 19 community using Odx UI components',
    'description': """
A fully customized backend theme for Odoo 19 community edition using Odx UI components.
    """,
    'author': 'Bashir Hassan',
    'website': 'https://www.odxbuilder.com/',
    'support': 'support@odxbuilder.com',
    'license': 'LGPL-3',
    'category': 'Themes/Backend',
    'depends': [
        'base',
        'web',
        'odx_owl'
    ],
    'data': [],
    'demo': [],
    'assets': {
        'web._assets_primary_variables': [
            (
                'after',
                'web/static/src/scss/primary_variables.scss',
                'odx_community_theme/static/src/scss/primary_variables.scss',
            ),
        ],
        'web.assets_backend': [
            'odx_community_theme/static/src/scss/_fonts.scss',
            'odx_community_theme/static/src/xml/webClient.xml',
            'odx_community_theme/static/src/xml/navbar.xml',
            'odx_community_theme/static/src/scss/web_client.scss',
            'odx_community_theme/static/src/scss/_animations.scss',
            'odx_community_theme/static/src/scss/_views.scss',
            'odx_community_theme/static/src/scss/_responsive.scss',
            'odx_community_theme/static/src/scss/_field_widgets.scss',
            'odx_community_theme/static/src/scss/_mail.scss',
            'odx_community_theme/static/src/js/sidebar_menu.js',
            'odx_community_theme/static/src/js/form_chatter_resize.js',
        ],
    },
    'images': [
        'static/description/Pipeline.jpeg',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
