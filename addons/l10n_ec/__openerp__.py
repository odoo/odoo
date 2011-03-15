# -*- coding: utf-8 -*-
##############################################################################
#
#    Copyright (C) 2010-2012 Cristian Salamea Gnuthink Software Labs Cia. Ltda
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
    'name': 'Ecuador - Accounting Chart',
    'version': '1.1',
    'category': 'Localisation/Account Charts',
    'description': """
    This is the base module to manage the accounting chart for Ecuador in OpenERP.
    ==============================================================================
    """,
    'author': 'OpenERP SA',
    'depends': [
                'account',
                'base_vat',
                'base_iban',
                'account_chart',
                'account_coda',
                ],
    'init_xml': [],
    'update_xml': [
                'account_tax_code.xml',
                'account_chart.xml',
                'account_tax.xml',
                'l10n_chart_ec_wizard.xml',
                   ],
    'demo_xml': [],
    'installable': True,
    'certificate' : '001226484516187330589',
    'images': ['images/config_chart_l10n_ec.jpeg','images/l10n_ec_chart.jpeg'],
}
