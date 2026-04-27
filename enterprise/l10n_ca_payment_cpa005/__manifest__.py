# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    "name": "CPA005 Payments",
    "summary": """Export payments as CPA 005 AFT files""",
    "category": "Accounting/Accounting",
    "description": """
Export payments as CPA 005 files for use in Canada.
    """,
    "version": "1.0",
    "depends": ["account_batch_payment", "l10n_ca"],
    "data": [
        "security/ir.model.access.csv",
        "data/l10n_ca_payment_cpa005.xml",
        "data/l10n_ca_cpa005.transaction.code.csv",
        "views/account_payment_views.xml",
        "views/account_journal_views.xml",
        "views/account_batch_payment_views.xml",
        "views/l10n_ca_cpa005_transaction_code_views.xml",
        "views/res_company_views.xml",
        "views/res_partner_bank_views.xml",
    ],
    "license": "OEEL-1",
    "auto_install": True,
}
