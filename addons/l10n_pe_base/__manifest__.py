# Copyright 2019 Vauxoo (https://www.vauxoo.com) <info@vauxoo.com>
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).
{
    'name': 'Base Localization for Odoo Peru not account',
    'version': '12.0.1.0.3',
    'category': 'Localization/Peru',
    'author': 'Vauxoo',
    'website': 'http://www.vauxoo.com/',
    "license": 'LGPL-3',
    'depends': [
        # 'contacts',
        'base_vat',
        'base_address_extended',
        'base_address_city',
    ],
    "data": [
        'security/ir.model.access.csv',
        'data/res_country_data.xml',
        'data/res.city.csv',
        'data/res.district.csv',
        'views/res_partner_view.xml',
    ],
    'installable': True,
}
