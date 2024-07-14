# coding: utf-8

{
    'name': 'Mexican Localization for eCommerce',
    'countries': ['mx'],
    'description': '''
Add an extra tab in the checkout process of the website/eCommerce with the mexican fields:

- l10n_mx_edi_cfdi_to_public (sale.order/account.move)
- l10n_mx_edi_fiscal_regime (res.partner)
- l10n_mx_edi_usage (sale.order/account.move)
- l10n_mx_edi_no_tax_breakdown (res.partner)

The extra tab only appears if:

- the company linked to the website is mexican
- the option 'automatic_invoice' is enabled in the website settings ("Generate the invoice automatically when the online payment is confirmed")
    ''',
    'version': '1.0',
    'category': 'Accounting/Localizations/EDI',
    'depends': [
        'website_sale',
        'l10n_mx_edi_sale',
    ],
    'data': [
        'views/templates.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            'l10n_mx_edi_website_sale/static/src/js/website_sale.js',
            # TODO in master: This should not be imported in the manifest, it
            # should be an ir.asset instead. We used this solution to be able to
            #  fix the bug without any module update.
            'l10n_mx_edi_website_sale/static/src/snippets/s_website_form/000.js',
        ],
        'web.assets_tests': [
            'l10n_mx_edi_website_sale/static/tests/tours/*.js',
        ],
    },
    'installable': True,
    'auto_install': True,
    'license': 'OEEL-1',
}
