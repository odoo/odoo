{
    "name": "Accounting (Enterprise Compatibility Wrapper)",
    "version": "19.0.1.0.0",
    "summary": "Expose Community accounting stack under the standard 'accountant' technical module name.",
    "category": "Accounting/Accounting",
    "license": "LGPL-3",
    "author": "Kodoo",
    "website": "https://kodoo.online",
    "depends": [
        "account",
        "om_account_accountant",
    ],
    "data": [
        "views/accountant_branding.xml",
    ],
    "pre_init_hook": "pre_init_hook",
    "application": False,
    "installable": True,
    "auto_install": False,
}
