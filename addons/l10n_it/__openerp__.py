# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2010
#    Italian OpenERP Community (<http://www.openerp-italia.org>)
#    Servabit srl
#    Agile Business Group sagl
#    Domsense srl
#    Albatos srl
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
    "name" : "Italy - Generic Chart of Accounts",
    "version" : "0.1",
    "depends" : ['base_vat','account_chart','base_iban'],
    "author" : "OpenERP Italian Community",
    "description": """
    Piano dei conti italiano di un'impresa generica
    """,
    "license": "AGPL-3",
    "category" : "Finance",
    'website': 'http://www.openerp-italia.org/',
    'init_xml': [
        ],
    'update_xml': [
        'data/account.account.type.csv',
        'data/account.account.template.csv',
        'data/account.tax.code.template.csv',
        'account_chart.xml',
        'data/account.tax.template.csv',
        'data/account.fiscal.position.template.csv',
        'l10n_chart_it_generic.xml',
        'report.xml',
        'libroIVA_view.xml',
        'libroIVA_menu.xml',
        'security/ir.model.access.csv',
        ],
    'demo_xml': [
        ],
    'installable': True,
    'active': False,
    'certificate' : '00926677190009155165',
}
