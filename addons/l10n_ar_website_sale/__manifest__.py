# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Argentinian Website',
    'version': '1.0',
    'category': 'Localization',
    'sequence': 14,
    'author': 'Odoo, ADHOC SA',
    'description': """
* Be able to see Identification Type and AFIP Responsibility in ecommerce checkout form.
* Show tax included/excluded groups applies only to the public/external users""",
    'depends': [
        'website_sale',
        'l10n_ar',
    ],
    'data': [
        'data/ir_model_fields.xml',
        'views/templates.xml',
        'views/res_config_settings_view.xml',
        'demo/website_demo.xml',
    ],
    'installable': True,
    'auto_install': True,
    'application': False,
}
