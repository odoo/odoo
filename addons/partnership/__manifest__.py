# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Partnership / Membership',
    'category': 'Sales/CRM',
    'description': """
This module allows you to manage all operations for managing memberships and partnerships.
==========================================================================================

You can easily assign grade to members/partners, with a specific pricelist.
    """,
    'depends': ['crm', 'sale'],
    'data': [
        'data/res_partner_grade_data.xml',
        'views/res_config_settings_views.xml',
        'views/res_partner_views.xml',
        'views/res_partner_grade_views.xml',
        'views/product_template_views.xml',
        'views/product_pricelist_views.xml',
        'views/partnership_menu.xml',
        'security/ir.access.csv',
    ],
    'author': 'Odoo S.A.',
    'license': 'LGPL-3',
}
