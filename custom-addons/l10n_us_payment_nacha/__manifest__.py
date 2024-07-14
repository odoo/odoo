# coding: utf-8
{
    "name": "NACHA Payments",
    'countries': ['us'],
    "summary": """Export payments as NACHA files""",
    "category": "Accounting/Accounting",
    "description": """
Export payments as NACHA files for use in the United States.
    """,
    "version": "1.0",
    "depends": ["account_batch_payment", "l10n_us"],
    "data": [
        "data/l10n_us_payment_nacha.xml",
        "views/account_journal_views.xml",
    ],
    "license": "OEEL-1",
    "auto_install": True,
}
