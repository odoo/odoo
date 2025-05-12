# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'author': 'Odoo',
    'name': 'Greece - myDATA',
    'version': '1.0',
    'category': 'Accounting/Localizations',
    'summary': """Connect to myDATA API implementation for Greece""",
    'description': """
        myDATA is a platform created by Greece's tax authority,
        The Independent Authority for Public Revenue (IAPR),
        to digitize business tax and accounting information declaration.
    """,
    'countries': ['gr'],
    'depends': ['l10n_gr'],
    'data': [
        'data/ir_cron.xml',
        'data/template.xml',
        'security/ir.model.access.csv',
        'views/account_fiscal_position_views.xml',
        'views/account_move_views.xml',
        'views/account_tax_views.xml',
        'views/product_template_views.xml',
        'views/report_invoice.xml',
        'views/res_company_views.xml',
        'views/res_config_settings_views.xml',
        'views/res_partner_views.xml',
    ],
    'installable': True,
    'auto_install': True,
    'license': 'LGPL-3',
}
