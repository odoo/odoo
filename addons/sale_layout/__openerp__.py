# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2014-Today OpenERP SA (<http://www.openerp.com>).
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
    'name': 'Sale Layout',
    'version': '1.0',
    'sequence': 14,
    'summary': 'Sale Layout, page-break, subtotals, separators, report',
    'description': """
Manage your sales reports
=========================
With this module you can personnalize the sale order and invoice report with
separators, page-breaks or subtotals.
    """,
    'author': 'OpenERP SA',
    'website': 'https://www.odoo.com/page/crm',
    'depends': ['sale', 'report'],
    'category': 'Sale',
    'data': ['views/sale_layout_category_view.xml',
             'views/report_invoice_layouted.xml',
             'views/report_quotation_layouted.xml',
             'views/sale_layout_template.xml',
             'security/ir.model.access.csv'],
    'demo': ['data/sale_layout_category_data.xml'],
    'installable': True,
}
