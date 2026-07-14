{
    'name': 'Türkiye - Nilvera E-Invoice Extended',
    'version': '1.0',
    'category': 'Accounting/Accounting',
    'description': """
This module enhances the core Nilvera integration by adding additional invoice scenarios and types required for Turkish e-Invoicing compliance.

Features include:
    1.Support for invoice scenarios: Basic, Export, and Public Sector
    2.Support for invoice types: Sales, Withholding, Tax Exempt, and Registered for Export
    3.Configuration of withholding reasons and exemption reasons
    4.Addition of Tax Offices.
    """,
    'depends': ['l10n_tr_nilvera_einvoice', 'contacts'],
    'data': [
        'security/ir.model.access.csv',
        'data/l10n_tr_nilvera_einvoice_extended.tax.office.csv',
        'data/account_incoterms_data.xml',
        'data/ubl_tr_templates.xml',
        'views/res_company_views.xml',
        'views/l10n_tr_nilvera_einvoice_extended_account_tax_code_views.xml',
        'views/l10n_tr_nilvera_einvoice_extended_tax_office_views.xml',
        'views/res_partner_views.xml',
        'views/account_move_views.xml',
        'views/account_tax_views.xml',
        'views/product_views.xml',
        'views/res_config_settings_views.xml',
    ],
    'auto_install': ['l10n_tr_nilvera_einvoice'],
    'installable': True,
    'post_init_hook': '_l10n_tr_nilvera_einvoice_extended_post_init',
    'license': 'LGPL-3',
}
