# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Website Sale - Project',
    'category': 'Website/Website',
    'summary': 'Bridge module between website_sale and project',
    'description': """
Bridge module between website_sale and project.
    """,
    'depends': ['website_sale', 'project'],
    'data': [
        'data/website_sale_project_data.xml',
    ],
    'auto_install': True,
    'assets': {
        'website.website_builder_assets': [
            'website_sale_project/static/src/website_builder/**/*',
        ],
    },
    'author': 'Odoo S.A.',
    'license': 'LGPL-3',
}
