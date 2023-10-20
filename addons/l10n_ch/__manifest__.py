# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Switzerland - Demo Data',
    'version': '1.0',
    'icon': '/account/static/description/l10n.png',
    'countries': ['ch'],
    'category': 'Localization/Demo Data',
    'description': """
This is the base module to create demonstration data for the Switzerland localization in Odoo.
==============================================================================================
    """,
    'depends': ['base'],
    'demo': [
        'demo/demo_company.xml',
        'demo/res_partner_demo.xml',
    ],
    'license': 'LGPL-3',
}
