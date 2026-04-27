{
    'name': 'Scan Vendor bills QRcode(India)',
    'version': '1.0',
    'description': """
This module enables the qrcode scanning feature for the vendor bills for india.
    """,
    'category': 'Accounting/Accounting',
    'depends': ['barcodes', 'l10n_in', 'account_invoice_extract'],
    'sequence': 1,
    'assets': {
        'web.assets_backend': [
            'l10n_in_qr_code_bill_scan/static/src/**/**/*',
        ],
    },
    'external_dependencies': {
        'python': ['pyjwt']
    },
    'auto_install': ['l10n_in'],
    'installable': True,
    'license': 'OEEL-1',
}
