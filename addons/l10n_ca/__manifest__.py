# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Canada - Accounting',
    'version': '1.1',
    'author': 'Savoir-faire Linux',
    'website': 'https://www.savoirfairelinux.com',
    'category': 'Accounting/Localizations/Account Charts',
    'description': """
This is the module to manage the Canadian accounting chart in Odoo.
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
position.
    """,
    'depends': [
        'account',
        'base_iban',
        'l10n_multilang',
    ],
    'data': [
        'data/account_chart_template_data.xml',
        'data/account.account.template.csv',
        'data/account_chart_template_after_data.xml',
        'data/account_tax_group_data.xml',
        'data/account_tax_data.xml',
        'data/fiscal_templates_data.xml',
        'data/account_chart_template_configure_data.xml',
        'data/res_company_data.xml',
        'views/res_partner_view.xml',
        'views/res_company_view.xml',
        'views/report_invoice.xml',
        'views/report_template.xml'
    ],
    'demo': [
        'demo/demo_company.xml',
    ],
    'post_init_hook': 'load_translations',
    'license': 'LGPL-3',
}
