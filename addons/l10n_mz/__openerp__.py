# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2014 3hConsulting, Lda. All Rights Reserved
#	 http://3hconsulting.blogspot.com/
#    $Id$
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
    'name': 'Mozambique - Chart of Accounts',
    'version': '0.001',
    'author': '3HConsulting',
    'website': 'http://3hconsulting.blogspot.com/',
    'category': 'Localization/Account Charts',
    'description': 'Plano de contas PGC-PE para Moçambique',
    'depends': ['base',
                'base_vat',
                'account',
                'account_chart',
                ],
    'init_xml': [],
    'update_xml': ['account_types.xml',
                   'account_chart.xml',
                   'account_tax_code_template.xml',
                   'account_chart_template.xml',
                   'fiscal_position_templates.xml',
                   'account_taxes.xml',
                   'l10n_chart_mz_wizard.xml',
                   ],
    'demo_xml': [],
    'installable': True,
}

