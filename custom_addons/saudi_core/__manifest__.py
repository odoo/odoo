{
    'name': 'Saudi Core Localization',
    'version': '1.0.0',
    'category': 'Localization',
    'author': 'abdulrhman7-star',
    'website': '',
    'license': 'OPL-1',
    'summary': 'Base Saudi Arabian Localization with Hijri support and address fields',
    'description': """
        - Hijri calendar and Arabic support.
        - Saudi partner fields and categories.
        - Default currency: SAR, multi-company enabled.
        - Saudi theme, RTL, translations.
        """,
    'depends': ['base', 'web'],
    'data': [
        'security/ir.model.access.csv',
        'security/saudi_core_security.xml',
        'data/res_partner_category.xml',
        'views/res_partner_views.xml',
        'views/res_config_settings_views.xml',
        'views/assets.xml',
    ],
    'qweb': [
        'static/src/xml/hijri_datepicker.xml',
    ],
    'static': [
        'static/src/js/*',
        'static/src/scss/*',
        'i18n/*',
    ],
    'installable': True,
    'auto_install': False,
    'application': False,
}
