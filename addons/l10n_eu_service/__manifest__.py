# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'EU Mini One Stop Shop (MOSS)',
    'category': 'Localization',
    'description': """
EU Mini One Stop Shop (MOSS) VAT for telecommunications, broadcasting and electronic services
=============================================================================================

As of January 1rst, 2015, telecommunications, broadcasting
and electronic services sold within the European Union
have to be always taxed in the country where the customer
belongs. In order to simplify the application of this EU
directive, the Mini One Stop Shop (MOSS) registration scheme
allows businesses to make a unique tax declaration.

This module makes it possible by helping with the creation
of the required EU fiscal positions and taxes in order to
automatically apply and record the required taxes.

This module installs a wizard to help setup fiscal positions
and taxes for selling electronic services inside EU.

The wizard lets you select:
 - the EU countries to which you are selling these
   services
 - your national VAT tax for services, to be mapped
   to the target country's tax
 - optionally: a template fiscal position, in order
   to copy the account mapping. Should be your
   existing B2C Intra-EU fiscal position. (defaults
   to no account mapping)
 - optionally: an account to use for collecting the
   tax amounts (defaults to the account used by your
   national VAT tax for services)

It creates the corresponding fiscal positions and taxes,
automatically applicable for EU sales with a customer
in the selected countries.
The wizard can be run again for adding more countries.

The wizard creates a separate Chart of Taxes for collecting the
VAT amounts of the MOSS declaration, so extracting the MOSS
data should be easy.
Look for a Chart of Taxes named "EU MOSS VAT Chart" in the
Taxes Report menu (Generic Accounting Report).

References
++++++++++
- Directive 2008/8/EC
- Council Implementing Regulation (EU) No 1042/2013

    """,
    'depends': ['account_accountant'],
    'data': [
        'security/ir.model.access.csv',
        'wizard/wizard.xml',
        'data/l10n_eu_service.service_tax_rate.csv',
        'views/account_settings_config_views.xml'
    ],
}
