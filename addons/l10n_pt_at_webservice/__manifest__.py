# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Portugal - AT Webservice',
    'website': 'https://www.odoo.com/documentation/master/applications/finance/fiscal_localizations.html',
    'icon': '/account/static/description/l10n.png',
    'category': 'Accounting/Localizations',
    'summary': 'Communicate AT series to the Autoridade Tributária through its webservice',
    'description': """
Connects Odoo to the webservices of the Portuguese Tax Authority (Autoridade Tributária, AT).

- AT Series: registers a series with the AT (SeriesWSService) and stores the validation code it
  returns, instead of entering the code obtained from the Portal das Finanças by hand.
- Settings: the webservice environment (offline by default, test or production) and the credentials.
  The calls go through Odoo's IAP proxy, which presents Odoo's client certificate to the AT. The AT
  public key certificate that encrypts the password is the same for every taxpayer and ships with
  the module.
    """,
    'depends': ['l10n_pt_certification'],
    'auto_install': ['l10n_pt_certification'],
    'data': [
        'views/l10n_pt_at_series_views.xml',
        'views/res_config_settings_views.xml',
    ],
    'author': 'Odoo S.A.',
    'license': 'LGPL-3',
}
