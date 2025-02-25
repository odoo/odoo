# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Members',
    'version': '1.0',
    'category': 'Sales/Sales',
    'description': """
    
    Todo


    """,
    'depends': ['base_geolocalize', 'crm', 'sale'],
    'data': [
        'security/ir.model.access.csv',
        'data/res_partner_grade_data.xml',
        'views/res_partner.xml',
        'views/res_parter_grade_views.xml',
        'views/product_template.xml',
    ],
    'website': 'https://www.odoo.com/app/forum',  #TODO
    'author': 'Odoo S.A.',
    'license': 'LGPL-3',
}
