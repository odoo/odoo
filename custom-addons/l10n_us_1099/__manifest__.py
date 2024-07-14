 # coding: utf-8
 # Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    "name": "1099 Reporting",
    'countries': ['us'],
    "summary": """Easily export 1099 data for e-filing with a 3rd party.""",
    "category": "Accounting/Accounting",
    "description": """
Allows users to easily export accounting data that can be imported to a 3rd party that does 1099 e-filing.
    """,
    "version": "1.0",
    "depends": [
        "l10n_us",
        "account_accountant",  # because we rely on bank reconciliation
    ],
    "data": [
        "security/ir.model.access.csv",
        "data/l10n_us.1099_box.csv",
        "views/res_partner_views.xml",
        "views/box_1099_views.xml",
        "wizard/generate_1099_wizard_views.xml",
    ],
    "demo": [
        "demo/res_partner_demo.xml",
    ],
    "license": "OEEL-1",
    "auto_install": True,
}
