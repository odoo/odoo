{
    'name': 'BBAN Plusgiro Bankgiro',
    'version': '1.0',
    'category': 'Accounting/Localizations',
    'author': 'XCLUDE',
    'summary': 'Implements BBAN Plusgiro Bankgiro',
    'description': """
        This adds support for BBAN, Plusgiro & Bankgiro for swedish accounts.
        It adapts the XML payment format for ISO20022 payments if the account number
        is a BBAN, Plusgiro or Bankgiro account.
        This module can be installed without installing the Swedish localization enabling
        the use of those accounts for non swedish companies.
    """,
    'depends': ['account_iso20022', 'l10n_se'],
    'data': [
        'data/se.bban.clear.range.csv',
        'security/ir.model.access.csv',
        'views/account_journal_views.xml',
        'views/se_bban_clear_range.xml',
    ],
    'auto_install': ['l10n_se'],
    'installable': True,
    'license': 'OEEL-1',
}
