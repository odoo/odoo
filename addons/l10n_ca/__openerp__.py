# -*- encoding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Canada - Accounting',
    'version': '1.2',
    'author': 'Savoir-faire Linux',
    'website': 'http://www.savoirfairelinux.com',
    'category': 'Localization/Account Charts',
    'description': """
This is the module to manage the English and French - Canadian accounting chart in OpenERP.
===========================================================================================

Canadian accounting charts and localizations.

Fiscal positions
----------------

When considering taxes to be applied, it is the province where the delivery occurs that matters. 
Therefore we decided to implement the most common case in the fiscal positions: delivery is the 
responsibility of the vendor and done at the customer location.

Some examples:

1) You have a customer from another province and you deliver to his location.
On the customer, set the fiscal position to his province.

2) You have a customer from another province. However this customer comes to your location
with their truck to pick up products. On the customer, do not set any fiscal position.

3) An international vendor doesn't charge you any tax. Taxes are charged at customs 
by the customs broker. On the vendor, set the fiscal position to International.

4) An international vendor charge you your provincial tax. They are registered with your
provincial government and remit taxes themselves. On the vendor, do not set any fiscal 
position.
    """,
    'depends': [
        'base',
        'account',
        'base_iban',
        'base_vat',
    ],
    'data': [
        'account_chart_en.xml',
        'account_chart_template_en.xml',
        'account_tax_en.xml',
        'fiscal_templates_en.xml',
        'account_chart_fr.xml',
        'account_chart_template_fr.xml',
        'account_tax_fr.xml',
        'fiscal_templates_fr.xml',
        'l10n_ca_wizard.xml'
    ],
    'demo': [],
    'installable': False,
}
