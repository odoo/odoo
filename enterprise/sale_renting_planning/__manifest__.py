# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': "Rental/Planning Bridge",
    'summary': """This module Integrate Planning with Rental""",
    'category': 'Hidden',
    'depends': ['sale_planning', 'sale_renting'],
    'auto_install': True,
    'license': 'OEEL-1',
    'uninstall_hook': 'uninstall_hook',
}
