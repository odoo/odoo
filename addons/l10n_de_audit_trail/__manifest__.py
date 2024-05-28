{
    'name': 'Germany - audit trail',
    'version': '1.0',
    'description': """
This module is a bridge to auto-install Audit Trail with Germany
    """,
    'summary': "Audit trail",
    'depends': [
        'l10n_de',
        'account_audit_trail'
    ],
    'installable': True,
    'auto_install': ['l10n_de'],
    'license': 'LGPL-3',
}
