# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': "Fidelity Management in Point of Sale",
    'summary': "Use discounts in Point of Sale.",
    'category': 'Sales',
    'depends': ['point_of_sale', 'fidelity'],
    'auto_install': True,
    'data': [
        'views/fidelity_pos_menu_views.xml',
        'views/fidelity_program_views.xml',
    ],
    'demo': [],
    'assets': {
        'point_of_sale._assets_pos': [
            'fidelity_pos/static/src/app/**/*',
        ],
    },
    'author': 'Odoo S.A.',
    'license': 'LGPL-3',
}
