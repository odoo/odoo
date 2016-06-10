# -*- encoding: utf-8 -*-
##############################################################################
#
#    Odoo, Open Source Business Applications
#    Copyright (C) 2015 Odoo S.A. <http://www.odoo.com>
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program. If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################
{
    'name': 'EU Mini One Stop Shop (MOSS)',
    'version': '1.0',
    'author': 'Odoo SA',
    'website': 'http://www.odoo.com',
    'category': '',
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
        'wizard/l10n_eu_service.service_tax_rate.csv'
    ],
    'test': [],
    'demo': [],
    'auto_install': False,
    'installable': True,
}
