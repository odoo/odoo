{
    "name": "Argentinean Electronic Invoicing WSMTXCA webservice",
    "summary": """
        This module adds the WSMTXCA webservice to the Argentinean Electronic Invoicing module.
        It allows to send electronic invoices to AFIP using the WSMTXCA webservice.
    """,
    "author": "Quilsoft",
    "website": "https://www.quilsoft.com",
    "license": "LGPL-3",
    "category": "Accounting",
    "version": "1.0",
    "email": "cmanuel.alvarez11@gmail.com",
    "installable": True,
    "application": False,
    "depends": [
        "l10n_ar_ux",
        "l10n_ar_edi",
        "account_accountant",
    ],
}
