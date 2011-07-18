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

{
    "name" : "Belgium - Multi language Chart of Accounts",
    "version" : "1.1",
    "author" : "OpenERP SA",
    "category": 'Localization/Account Charts',
    "description": """
    Belgian localisation (on top of l10n_be):
    * Multilanguage support for Chart of Accounts, Taxes, Tax Codes and Journals
    * Multilingual accounting templates
    * Multilanguage support Analytic Chart of Accounts and Analytic Journals
    * Update partner titles for commonly used legal entities
    * Add constraint to ensure unique Tax Code per Company 
    * Setup wizard changes
        - Copy translations for CoA, Tax, Tax Code and Fiscal Position from templates to target objects
        - Add options to install languages during the setup
        - Generate Financial Journals from the templates
    """,
    'website': 'http://www.openerp.com',
    'init_xml': [],
    "depends" : ['account_accountant'],
    'update_xml': [
    ],
    'demo_xml': [
    ],
    'installable': True,
    'active': False,
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
