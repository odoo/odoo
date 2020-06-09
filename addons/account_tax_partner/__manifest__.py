# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Use taxes with aliquots per partner',
    'version': '1.0',
    'category': 'Accounting/Accounting',
    'sequence': 14,
    'author': 'Odoo, ADHOC SA',
    'description': """
""",
    'depends': [
        'account',
    ],
    'data': [
        'views/res_partner_view.xml',
        'security/ir.model.access.csv',
    ],
    'installable': True,
    'auto_install': False,
    'application': False,
}
