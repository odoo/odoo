# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Test HTTP',
    'version': '1.0',
    'category': 'Hidden/Tests',
    'description': """A module to test HTTP""",
    'depends': ['web', 'web_tour', 'mail', 'rpc'],
    'installable': True,
    'data': [
        'data/data.xml',
        'security/ir.model.access.csv',
        'views/views.xml',
    ],
    'author': 'Odoo S.A.',
    'license': 'LGPL-3',
}
