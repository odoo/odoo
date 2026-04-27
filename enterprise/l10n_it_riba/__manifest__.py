{
    'name': 'Italy - Bank Receipts (Ri.Ba.)',
    'icon': '/account/static/description/l10n.png',
    'version': '0.1',
    'depends': [
        'l10n_it_edi',
        'base_iban',
        'account_batch_payment'
    ],
    'auto_install': ['l10n_it_edi'],
    'author': 'Odoo',
    'description': """
Ri.Ba. Export for Batch Payment
================================

This module enables the generation of Ri.Ba. (Ricevute Bancarie) files from batch payments in Odoo.  
It facilitates compliance with the Italian banking standard for managing receivables.

- Group multiple receivables into a single batch for streamlined management and reconciliation.
- Export batch payments as RIBA-compliant files to be submitted to your homebanking for processing.

For more information about RIBA standards, refer to the guidelines issued by the Italian Bankers Association (CBI).
    """,
    'category': 'Accounting/Localizations',
    'website': 'http://www.odoo.com/',
    'data': [
        'data/account_payment_method_data.xml',
        'views/res_company_views.xml'
    ],
    'demo': ['demo/res_company_demo.xml'],
    'license': 'LGPL-3',
}
