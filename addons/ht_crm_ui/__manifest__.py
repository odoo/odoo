{
    'name': "HT CRM UI",

    'summary': "UI enhancements for CRM (list view, column resize, UX tweaks)",

    'description': """
Frontend improvements for Odoo CRM:
- Column width control
- List view enhancements
- OWL-based UI patches
    """,

    'author': "My Company",
    'website': "https://www.yourcompany.com",

    'category': 'Hidden',  # keep it out of Apps unless needed
    'version': '1.0.0',

    'depends': ['web'],

    'assets': {
        'web.assets_backend': [
            'ht_crm_ui/static/src/js/*.js',
            'ht_crm_ui/static/src/xml/*.xml',
            'ht_crm_ui/static/src/css/*.css',
        ],
    },

    'data': [],

    'installable': True,
    'application': False,
    'auto_install': False,
}