# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Mail Tips',
    'category': 'Usability',
    'description': """
OpenERP link module for web tips.
=================================

""",
    'version': '0.1',
    'depends': ['web_tip', 'mail'],
    'data': [
        'views/mail_tip.xml',
    ],
    'auto_install': True
}
