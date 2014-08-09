# -*- coding: utf-8 -*-
##############################################################################
#
# Copyright (c) 2014 Marcos Organizador de Negocios- Eneldo Serrata - http://marcos.do
#
# WARNING: This program as such is intended to be used by professional
# programmers who take the whole responsability of assessing all potential
# consequences resulting from its eventual inadequacies and bugs.
# End users who are looking for a ready-to-use solution with commercial
# garantees and support are strongly adviced to contract a Free Software
# Service Company like Marcos Organizador de Negocios.
#
# This program is Free Software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301  USA
#
##############################################################################

{
    'name': 'Dominican Republic - NCF',
    'version': '1.0',
    'category': 'Others',
    'description': """
This is the base module to manage the NCF implementation for Dominican Republic.
======================================================================

    * Chart of Accounts.
    * The Tax Code Chart for Domincan Republic
    * The main taxes used in Domincan Republic
    * Fiscal position for local """,
    'author': 'Marcos Organizador de Negocios, SRL.',
    'website': 'http://marcos.do',
    'depends': ['base',
                'base_vat',
                'base_iban',
                'account',
                'account_voucher',
                'stock',
                'stock_account',
                'purchase', 'sale',
                'point_of_sale',
                'product'],
    'data': [
        'res/res_view.xml',
        'account/account_view.xml',
        'account/wizard/account_invoice_debit_view.xml',
        'account/account_invoice_view.xml',
        'stock/stock_view.xml',
        'stock/wizard/stock_account_move_view.xml',
        'stock/wizard/nc_from_stock.xml',
        'product/product_view.xml',
        'sale/sale_view.xml',
        'point_of_sale/wizard/pos_payment_view.xml',
        'point_of_sale/point_of_sale_view.xml'
    ],
    'test': [],
    'demo': [],
    'installable': True,
    'auto_install': False,
    'images': ['images/config_chart_l10n_lu.jpeg','images/l10n_lu_chart.jpeg'],
}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
