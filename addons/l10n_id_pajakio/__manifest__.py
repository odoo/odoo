# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Indonesia - Pajak.io Integration',
    'icon': '/account/static/description/l10n.png',
    'version': '1.0',
    'description': """
        Integration with Pajak.io in order to send e-invoiced data
        which will streamline the process of reporting to the tax authority (DJP).
    """,
    'category': 'Accounting/Localizations/EDI',
    'depends': [
        'l10n_id_efaktur_coretax',
        'iap',
        'phone_validation',
    ],
    'data': [
        "data/iap_service_data.xml",
        "data/ir_cron_data.xml",
        "security/ir.model.access.csv",
        "views/efaktur_document.xml",
        "views/iap_account_views.xml",
        "views/res_config_settings_views.xml",
        "wizard/register.xml",
        "wizard/l10n_id_pajakio_invoice_cancel.xml",
    ],
    'installable': True,
    'author': 'Odoo S.A.',
    'license': 'LGPL-3',
}
