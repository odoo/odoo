{
    'name': 'Remove default zero',

    'author': 'Kitworks Systems',
    'website': 'https://kitworks.systems/',

    'category': 'Extra Tools',
    'license': 'OPL-1',
    'version': '16.0.2.0.3',

    'depends': ['web', ],
    'data': ['views/templates.xml', ],
    'installable': True,

    'images': [
        'static/description/cover.png',
        'static/description/icon.png',
    ],
    'assets': {
        'web.assets_backend': [
            'kw_remove_default_zero/static/src/js/kw_remove_default_zero.js'],
    },
}
