{
    'name': 'Argentinian demo data',
    'version': '12.0.1.0.0',
    'category': 'Accounting',
    'summary': '',
    'author': 'ADHOC SA',
    'website': 'www.adhoc.com.ar',
    'license': 'AGPL-3',
    'images': [
    ],
    'depends': [
        'account_accountant',
        'l10n_ar',
        # 'l10n_ar_afipws_fe',
        # 'l10n_ar_chart',
        # 'l10n_ar_account_tax_settlement',
        # 'l10n_ar_account_withholding',
    ],
    # 'data': [
    # ],
    'data': [
        'demo/account_tax_template_demo.xml',
        'demo/res_company_demo.xml',
        'demo/product_product_demo.xml',
        'demo/partner_demo.xml',
        'demo/account_customer_invoice_demo.xml',
        'demo/account_customer_expo_invoice_demo.xml',
        'demo/account_customer_invoice_validate_demo.xml',
        'demo/account_customer_refund_demo.xml',
        'demo/account_supplier_invoice_demo.xml',
        'demo/account_supplier_invoice_validate_demo.xml',
        'demo/account_supplier_refund_demo.xml',
        # TODO waiting for l10n_ar_edi
        # '../l10n_ar_afipws_fe/demo/account_journal_expo_demo.yml',
        # '../l10n_ar_afipws_fe/demo/account_journal_demo.yml',
        # '../l10n_ar_afipws_fe/demo/account_journal_demo_without_doc.yml',
    ],
    'test': [
    ],
    'installable': True,
    'auto_install': False,
    'application': False,
}
