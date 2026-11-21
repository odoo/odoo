# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Company Timezone from City',
    'summary': "Set the companies' timezone from their city",
    'category': 'Hidden',
    'description': """
Bridge between Resource and City Timezones: in countries with several
timezones, the timezone of a company is the one of its city.
    """,
    'depends': ['resource', 'base_city_timezone'],
    'auto_install': True,
    'author': 'Odoo S.A.',
    'license': 'LGPL-3',
}
