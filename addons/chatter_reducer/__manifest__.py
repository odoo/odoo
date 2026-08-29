{
    'name': 'Chatter Reducer',
    'version': '19.5.1.0',
    'category': 'Tools',
    'summary': 'Shrinks/hides the chatter panel globally across all form views',
    'author': 'JUPE',
    'depends': ['mail'],
    'assets': {
        'web.assets_backend': [
            'chatter_reducer/static/src/scss/chatter_reducer.scss',
            'chatter_reducer/static/src/js/systray_chatter_toggle.js',
            'chatter_reducer/static/src/xml/systray_chatter_toggle.xml',
        ],
    },
    'installable': True,
    'application': False,
}