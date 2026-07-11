{
    'name': 'Web Font Awesome 6',
    'version': '19.0.1.0.0',
    'category': 'Hidden/Tools',
    'summary': 'Reskin the whole UI with Font Awesome 6 Free, overriding the '
               'bundled Font Awesome 4 without touching any view.',
    'description': """
Font Awesome 6 for Odoo
=======================

Odoo ships Font Awesome 4.7 and hardcodes ``fa fa-*`` classes in hundreds of
views. This module loads Font Awesome 6 Free (plus the official v4 -> v6
compatibility shims) *after* the core Font Awesome assets, so every existing
``fa fa-*`` icon renders the newer FA6 glyph. No view is modified; uninstall to
revert.
""",
    'depends': ['web'],
    'assets': {
        # Loaded after `web`'s own Font Awesome (this module depends on web), so
        # our `.fa` font-family + the v4 shims win by source order.
        'web.assets_backend': [
            'web_fontawesome6/static/src/lib/fontawesome6/css/all.min.css',
            'web_fontawesome6/static/src/lib/fontawesome6/css/v4-shims.min.css',
        ],
        'web.assets_frontend': [
            'web_fontawesome6/static/src/lib/fontawesome6/css/all.min.css',
            'web_fontawesome6/static/src/lib/fontawesome6/css/v4-shims.min.css',
        ],
    },
    'license': 'LGPL-3',
    'installable': True,
    'application': False,
    'auto_install': True,
}
