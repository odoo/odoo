# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': "Report Engine: wkhtmltopdf/wkhtmltoimage",
    'summary': "wkhtmltopdf rendering engine",
    'version': '1.0',
    'description': """
This module is the implementation of the wkhtmltopdf and
wlhtmltoimage rendering engine for Odoo.

learn more about it here:
https://wkhtmltopdf.org/
    """,
    'category': 'Hidden/Tools',
    'auto_install': True,
    'post_init_hook': 'post_init_hook',
    'author': 'Odoo S.A.',
    'license': 'LGPL-3',
}
