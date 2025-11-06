{
    'name': 'Türkiye - Nilvera E-Invoice',
    'category': 'Accounting/Accounting',
    'description': """
For sending and receiving electronic invoices to Nilvera.

Features include:

- Support for invoice scenarios: Basic, Export, and Public Sector
- Support for invoice types: Sales, Withholding, Tax Exempt, and Registered for Export
- Configuration of withholding reasons and exemption reasons
- Addition of Tax Offices.
    """,
    'depends': ['l10n_tr_nilvera', 'account_edi_ubl_cii', 'contacts'],
    'data': [
        'security/ir.model.access.csv',
        'data/cron.xml',
        'data/res_partner_category_data.xml',
        'data/l10n_tr_nilvera_einvoice.tax.office.csv',
        'data/account_incoterms_data.xml',
        'data/ubl_tr_templates.xml',
        'views/res_company_views.xml',
        'views/l10n_tr_nilvera_einvoice_account_tax_code_views.xml',
        'views/l10n_tr_nilvera_einvoice_tax_office_views.xml',
        'views/res_partner_views.xml',
        'views/account_move_views.xml',
        'views/account_tax_views.xml',
        'views/product_views.xml',
        'views/res_config_settings_views.xml',
    ],
    'demo': [
        'demo/demo_company.xml',
    ],
    'auto_install': ['l10n_tr_nilvera'],
    'author': 'Odoo S.A.',
    'license': 'LGPL-3',
}
