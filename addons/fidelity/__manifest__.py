# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': "Fidelity Management",
    'summary': "Use discounts in sales channels",
    'category': 'Sales',
    'depends': ['product', 'portal', 'account'],
    'data': [
        'security/ir.model.access.csv',
        'views/fidelity_program_views.xml',
        'views/fidelity_reward_views.xml',
        'views/fidelity_rule_views.xml',
        'views/fidelity_card_views.xml',
        'views/portal_template_views.xml',
        'views/fidelity_transaction_views.xml',
        'views/fidelity_balance_views.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            'fidelity/static/src/js/portal/**/*',
            'fidelity/static/src/interactions/*',
        ],
        'web.assets_backend': [
            'fidelity/static/src/backend/**/*',
        ],
    },
    'author': 'Odoo S.A.',
    'license': 'LGPL-3',
}
