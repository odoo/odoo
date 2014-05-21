# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2009 Tiny SPRL (<http://tiny.be>).
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
    'name': 'Assets & Revenue Recognitions Management',
    'version': '1.0',
    'depends': ['account'],
    'author': 'OpenERP S.A.',
    'description': """
Assets management.
==========================================

It allows you to manage the assets owned by a company or a person.
It keeps track of the depreciation occurred on those assets, and creates account moves for those depreciation lines.

Revenue recognitions.
===========================================
It allows you to manage the revenue recognition on product's sale.
It keeps track of the installments occurred on those revenue recognition, and creates account moves for those installment lines.

    """,
    'website': 'http://www.openerp.com',
    'category': 'Accounting & Finance',
    'sequence': 32,
    'demo': [ 'account_asset_demo.xml'],
    'test': [
        'test/account_asset_demo.yml',
        'test/account_asset.yml',
        'test/account_asset_wizard.yml',
        'test/account_revenue_recognition_demo.yml',
        'test/account_revenue_recognition.yml',
    ],
    'data': [
        'security/account_asset_security.xml',
        'security/ir.model.access.csv',
        'wizard/account_asset_change_duration_view.xml',
        'wizard/wizard_asset_compute_view.xml',
        'account_asset_view.xml',
        'account_asset_invoice_view.xml',
        'report/account_asset_report_view.xml',
    ],
    'auto_install': False,
    'installable': True,
    'application': False,
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

