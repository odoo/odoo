# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'France - Accounting',
    'website': 'https://www.odoo.com/documentation/master/applications/finance/fiscal_localizations/france.html',
    'icon': '/account/static/description/l10n.png',
    'countries': ['fr'],
    'version': '2.2',
    'category': 'Accounting/Localizations/Account Charts',
    'description': """
This is the module to manage the accounting chart for France in Odoo.
========================================================================

This module applies to companies based in France mainland. It doesn't apply to
companies based in the DOM-TOMs (Guadeloupe, Martinique, Guyane, Réunion, Mayotte).

This localisation module creates the VAT taxes of type 'tax included' for purchases
(it is notably required when you use the module 'hr_expense'). Beware that these
'tax included' VAT taxes are not managed by the fiscal positions provided by this
module (because it is complex to manage both 'tax excluded' and 'tax included'
scenarios in fiscal positions).

This localisation module doesn't properly handle the scenario when a France-mainland
company sells services to a company based in the DOMs. We could manage it in the
fiscal positions, but it would require to differentiate between 'product' VAT taxes
and 'service' VAT taxes. We consider that it is too 'heavy' to have this by default
in l10n_fr_account; companies that sell services to DOM-based companies should update the
configuration of their taxes and fiscal positions manually.

**Credits:** Sistheo, Zeekom, CrysaLEAD, Akretion and Camptocamp.
""",
    'depends': [
        'base_iban',
        'base_vat',
        'account',
        'l10n_fr',
    ],
    'auto_install': ['account'],
    'data': [
        'data/account_chart_template_data.xml',
        'data/tax_report_data.xml',
        'views/report_invoice.xml',
        'wizard/account_fr_fec_export_wizard_view.xml',
        'security/ir.model.access.csv',
        'data/res.bank.csv',
    ],
    'demo': [
        'data/l10n_fr_account_demo.xml',
    ],
    'post_init_hook': '_l10n_fr_post_init_hook',
    'license': 'LGPL-3',
}
