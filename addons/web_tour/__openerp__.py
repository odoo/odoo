# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Tours',
    'category': 'Usability',
    'description': """
Odoo Web tours.
========================

""",
    'version': '0.1',
    'depends': ['web'],
    'data': [
        'assets.xml',
        'views/tour.xml'
    ],
    'qweb': [
        "static/src/xml/*.xml",
    ],
    'auto_install': True
}
