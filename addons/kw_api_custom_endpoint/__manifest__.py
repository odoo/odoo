{
    'name': 'Custom API controller',
    'version': '16.0.1.6.0',
    'license': 'LGPL-3',
    'category': 'Extra Tools',

    'author': 'Kitworks Systems',
    'website': 'https://kitworks.systems/',

    'images': [
        'static/description/cover.png',
        'static/description/icon.png',
    ],

    'depends': [
        'kw_api',
    ],

    'external_dependencies': {
        'python': ['html2text', ],
    },

    'data': [
        'security/ir.model.access.csv',

        'views/custom_endpoint_views.xml',
    ],

    'installable': True,
}
