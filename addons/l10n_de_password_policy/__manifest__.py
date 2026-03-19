{
    'name': 'Germany - Password Policy',
    'author': 'Odoo S.A.',
    'category': 'Hidden/Tools',
    'summary': 'Enforce password policy for German GoBD compliance',
    'description': """
Germany - Password Policy Bridge
=================================
This bridge module ensures that the ``auth_password_policy`` module is
automatically installed alongside the German accounting localisation
(``l10n_de``) to satisfy GoBD certification requirements.
    """,
    'depends': [
        'l10n_de',
        'auth_password_policy',
    ],
    'auto_install': ['l10n_de'],
    'license': 'LGPL-3',
}
