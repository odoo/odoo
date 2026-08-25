# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    "name": "Taiwan - E-invoicing",
    "countries": ["tw"],
    'icon': '/account/static/description/l10n.png',
    "category": "Accounting/Localizations/EDI",
    "summary": """E-invoicing using ECpay""",
    "description": """
<<<<<<< 7a7db9dbf4516808d20860ba6b91c879f8bbaca8
        Taiwan - E-invoicing
        =====================
        This module allows the user to send their invoices to the Ecpay system.
    """,
||||||| 6fc51dd2bdca9f189247c9fc9f7a12776babb72b
        Taiwan - E-invoicing
        =====================
        This module allows the user to send their invoices to the Ecpay system.
    """,
    "website": "https://www.odoo.com",
=======
Taiwan - E-invoicing
====================
This module allows the user to send their invoices to the Ecpay system.
""",
    "website": "https://www.odoo.com",
>>>>>>> 645698619e2b8bf264eab5b14ba56d0ad0e6c3f5
    'author': 'Odoo S.A.',
    "license": "LGPL-3",
    "depends": ["l10n_tw", "base_vat"],
    "data": [
        "security/ir.model.access.csv",
        "views/res_config_setting_view.xml",
        "views/account_tax.xml",
        "views/account_move_view.xml",
        "views/account_move_reversal_view.xml",
        "views/l10n_tw_edi_invoice_cancel_view.xml",
        "views/l10n_tw_edi_invoice_print_view.xml",
    ],
    "uninstall_hook": "uninstall_hook",
}
