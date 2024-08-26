{
    'name': 'Import One Stop Shop (IOSS)',
    'category': 'Accounting/Localizations',
    'description': """

This module is a complement for the OSS module.
It allows non European countries to use the OSS system by chosing a host country in the EU and also have a set of fiscal position from install.

    """,
    'depends': ['l10n_eu_oss'],
    'data': [
        'views/res_config_settings_views.xml',
    ],
    'auto_install': True,
    'post_init_hook': 'l10n_extra_eu_oss_post_init',
    'uninstall_hook': 'l10n_extra_eu_oss_uninstall',
    'license': 'LGPL-3',
}
