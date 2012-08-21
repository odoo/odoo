# -*- encoding: utf-8 -*-
#################################################################################
#
#    Copyright (C) 2009  Renato Lima - Akretion
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
#################################################################################

{
    'name': 'Brazilian - Accounting',
    'category': 'Localization/Account Charts',
    'description': """
Base module for the Brazilian localization.
===========================================

This module consists in:

 - Generic Brazilian chart of accounts
 - Brazilian taxes such as:

        - IPI
        - ICMS
        - PIS
        - COFINS
        - ISS
        - IR
        - IRPJ
        - CSLL

 - Tax Situation Code (CST) required for the electronic fiscal invoicing (NFe)

The field tax_discount has also been added in the account.tax.template and account.tax
objects to allow the proper computation of some Brazilian VATs such as ICMS. The
chart of account creation wizard has been extended to propagate those new data properly.

It's important to note however that this module lack many implementations to use
OpenERP properly in Brazil. Those implementations (such as the electronic fiscal
Invoicing which is already operational) are brought by more than 15 additional
modules of the Brazilian Launchpad localization project
https://launchpad.net/openerp.pt-br-localiz and their dependencies in the extra
addons branch. Those modules aim at not breaking with the remarkable OpenERP
modularity, this is why they are numerous but small. One of the reasons for
maintaining those modules apart is that Brazilian Localization leaders need commit
rights agility to complete the localization as companies fund the remaining legal
requirements (such as soon fiscal ledgers, accounting SPED, fiscal SPED and PAF
ECF that are still missing as September 2011). Those modules are also strictly
licensed under AGPL V3 and today don't come with any additional paid permission
for online use of 'private modules'.""",
    'license': 'AGPL-3',
    'author': 'Akretion, OpenERP Brasil',
    'website': 'http://openerpbrasil.org',
    'version': '0.6',
    'depends': ['account','account_chart'],
    'init_xml': [        
        'data/account.account.type.csv',
        'data/account.tax.code.template.csv',
        'data/account.account.template.csv',
        'data/l10n_br_account_chart_template.xml',
        'data/account_tax_template.xml',
        'data/l10n_br_data.xml',
        'security/ir.model.access.csv',
                ],
    'update_xml': [
        'account_view.xml',
        'l10n_br_view.xml',
    ],
    'installable': True,
    'certificate' : '001280994939126801405',
}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
