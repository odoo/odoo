# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Peruvian eCommerce',
    'version': '1.0',
    'category': 'Accounting/Localizations/Website',
    'sequence': 14,
    'author': 'Vauxoo, Odoo',
    'description': """Be able to see Identification Type in ecommerce checkout form.""",
    'depends': [
        'website_sale',
        'l10n_pe',
    ],
    'data': [
        'data/ir_model_fields.xml',
        'views/templates.xml',
    ],
    'demo': [
        'demo/website_demo.xml',
    ],
    'installable': True,
    'auto_install': True,
    'license': 'LGPL-3',
}
