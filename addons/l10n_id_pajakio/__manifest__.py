# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Pajak.io Integration',
    'icon': '/account/static/description/l10n.png',
    'version': '1.0',
    'description': """
        Integration with Pajak.io in order to send e-invoiced data
        which will streamline the process of reporting to the tax authority (DJP).
    """,
    'category': 'Accounting/Localizations/EDI',
    'depends': ['l10n_id_efaktur_coretax'],
    'data': [
        "data/iap_service_data.xml",
        "security/ir.model.access.csv",
        "views/res_config_settings.xml",
        "views/account_move.xml",
        "wizard/register.xml",
    ],
    'installable': True,
    'author': 'Odoo S.A.',
    'license': 'LGPL-3',
}
