# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
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
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

#
# This module provides a minimal UK chart of accounts for building upon further
# OpenERP's default currency and accounts are remapped to this chart
#
# This module works for OpenERP 4.1.0 (and, assumed, onwards).
# This module does not work for OpenERP 4.0.2 and before.
#
# VAT is structured thus:
#  - the user company is assumed to be non-VAT exempt (easy to modify, however)
#  - categories OVATS (Standard), OVATR (Reduced), OVATZ (Zero) should be
#    assigned to the customer taxes section of products (depending on the product)
#  - categories IVATS (Standard), IVATR (Reduced), IVATZ (Zero) should be
#    assigned to the supplier taxes section of products (depending on the product)
#  - categories OVATX (eXempt), OVATO (Out of scope), or nothing at all should be
#    assigned to default tax field of customers (depending on the customer)
#  - customer categorization trumps product categorization (unchanged Tiny functionality)
#  - on purchases, upon invoicing
#    - the base amount (ex-VAT) appears in the appropriate input base category (S, R, Z)
#    - the VAT amount appears in the appropriate input VAT category (S, R)
#    - invoice lines can be traced in these VAT categories
#    - refunds of invoices are deducted from the input category
#  - on sales, upon invoicing
#    - the base amount (ex-VAT) appears in the appropriate output base category (S, R, Z, X, O)
#    - the VAT amount appears in the appropriate output VAT category (S, R)
#    - invoice lines can be traced in these VAT categories
#    - refunds of invoices are deducted from the output category
#
# This forms a basis for accrual tax accounting
# Cash tax accounting can be accommodated with further processing in OpenERP
#
# Status beta 0.92 - tested on OpenERP 4.1.0
# Status beta 0.93 - tested on OpenERP 4.1.0
# - trivial change to depend only on 'account'
#   (seemed to be important for importing with no demo data)
# Status 1.0 - tested on OpenERP 4.1.0, 4.0.3
# - COGS account type fixed
#

{
    'name': 'United Kingdom - minimal',
    'version': '1.1',
    'category': 'Finance',
    'description': """
    This is the base module to manage the accounting chart for United Kingdom in OpenERP.
    =====================================================================================
    """,
    'author': 'Seath Solutions Ltd',
    'website': 'http://www.seathsolutions.com',
    'depends': ['base_iban', 'base_vat', 'account_chart'],
    'init_xml': [],
    'update_xml': [
        'l10n_uk_types.xml',
        'l10n_uk_chart.xml',
        'l10n_uk_tax.xml',
        'l10n_uk_wizard.xml'
    ],
    'demo_xml': [],
    'installable': True,
    'active': False,
    'certificate': '008956603329629',
    'images': ['images/config_chart_l10n_uk.jpeg','images/l10n_uk_chart.jpeg'],
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
