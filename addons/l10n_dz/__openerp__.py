# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2014 Tech Receptives (<http://techreceptives.com>).
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
    'name': 'Algeria - Accounting',
    'version': '1.0',
    'author': 'Mohamed Amine Azzi from Novisoft Algeria',
    'website': 'http://www.novisoft.net',
    'category': 'Localization/Account Charts',
    'description': """
Algeria accounting chart and localization.
=======================================================

    """,
    'depends': ['base', 'account', 'account_chart', 'base_vat'],
    'demo': [ ],
    'data': [
             'l10n_dz_account_chart.xml',
             'l10n_dz_tax_chart.xml',
             'l10n_dz_tax.xml',
             'l10n_dz_wizard.xml',
    ],
    'installable': True,
}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
