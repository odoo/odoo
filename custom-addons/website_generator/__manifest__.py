# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Website Generator',
    'version': '1.0.0',
    'category': 'Hidden/Tools',
    'summary': 'Import a pre-existing website',
    'description': """
        Generates a new website in Odoo, with the goal of recreating an external website as close as possible.
    """,
    'depends': ['website'],
    'data': [
        'security/ir.model.access.csv',
        'cron/cron.xml',
        'views/website_generator_views.xml',
        'data/website_generator_data.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'website_generator/static/src/client_actions/*/*',
            'website_generator/static/src/systray_items/*',
        ],
    },
    'installable': True,
    'license': 'OEEL-1',
}
