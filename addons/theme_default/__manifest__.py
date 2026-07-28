# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Default Theme',
    'description': 'Default website theme',
    'category': 'Theme',
    'sequence': 1000,
    'depends': ['website'],
    'data': [
        'data/generate_primary_template.xml',
        'views/snippets/s_company_team.xml',
        'views/snippets/s_text_image.xml',
        'views/snippets/s_image_text.xml',
    ],
    'images': [
        'static/description/cover.png',
        'static/description/theme_default_screenshot.jpg',
    ],
    'author': 'Odoo S.A.',
    'license': 'LGPL-3',
}
