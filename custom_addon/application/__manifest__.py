{
    'name': "Application",
    'version': '1.0',
    'summary': """""",
    'description': """""",
    'category': 'Services/Project',
    'live_test_url': '',
    'author': 'phuongtn',
    'company': '',
    'maintainer': '',
    'website': "",
    'depends': [
        'base'
    ],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'views/application_view.xml',
        'views/application_menu.xml',
        'data/status_data_default.xml'
    ],
    'assets': {
        'web.assets_backend': [
        ],
        'web.assets_qweb': [
        ],
    },

    'images': [],
    'license': "AGPL-3",
    'installable': True,
    'application': True,
}