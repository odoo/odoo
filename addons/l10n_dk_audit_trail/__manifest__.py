{
    'name': 'Denmark - audit trail',
    'version': '1.0',
    'description': """
This module is a bridge to be able to have audit trail module with Denmark
    """,
    'summary': "Audit trail",
    'countries': ['dk'],
    'depends': [
        'l10n_dk',
        'account_audit_trail'
    ],
    'installable': True,
    'auto_install': ['l10n_dk'],
    'license': 'LGPL-3',
}
