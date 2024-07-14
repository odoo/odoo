# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Mass mailing on sale subscriptions',
    'category': 'Hidden',
    'version': '1.0',
    'summary': 'Add sale subscription support in mass mailing',
    'description': """Mass mailing on sale subscriptions""",
    'depends': [
        'mass_mailing_sale',
        'sale_subscription',
    ],
    'auto_install': True,
    'license': 'OEEL-1',
}
