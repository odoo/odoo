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
    'post_init_hook': '_l10n_dk_audit_trail_post_init',
    'installable': True,
    'auto_install': True,
    'license': 'LGPL-3',
}
