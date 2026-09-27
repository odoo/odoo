# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Google Maps',
    'category': 'Website/Website',
    'summary': 'Show your company address on Google Maps',
    'description': """
Show your company address/partner address on Google Maps. Configure an API key in the Website settings.
    """,
    'depends': ['base_geolocalize', 'website_partner'],
    'data': [
        'views/google_map_templates.xml',
    ],
    'author': 'Odoo S.A.',
    'license': 'LGPL-3',
}
