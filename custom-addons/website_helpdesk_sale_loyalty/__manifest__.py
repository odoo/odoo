# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': "website helpdesk sale",
    'summary': "website helpdesk sale loyalty",
    'category': 'Services/Helpdesk',
    'depends': ['website_sale_loyalty', 'helpdesk_sale_loyalty'],
    'description': """
This module installs when we want to share coupon from helpdesk.
    """,
    'data': [
        'wizard/website_helpdesk_share_coupon_generate_views.xml',
    ],
    'version': '1.0',

    'auto_install': True,
    'license': 'OEEL-1',
}
