# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    
#    Copyright (c) 2011 Noviat nv/sa (www.noviat.be). All rights reserved.
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
    'name': 'Bank Statement Extensions to Support e-banking',
    'version': '0.3',
    'license': 'AGPL-3',
    'author': 'Noviat',
    'category': 'Generic Modules/Accounting',
    'description': '''
Module that extends the standard account_bank_statement_line object for improved e-banking support.
===================================================================================================

This module adds:
-----------------
    - valuta date
    - batch payments
    - traceability of changes to bank statement lines
    - bank statement line views
    - bank statements balances report
    - performance improvements for digital import of bank statement (via 
      'ebanking_import' context flag)
    - name_search on res.partner.bank enhanced to allow search on bank 
      and iban account numbers
    ''',
    'depends': ['account'],
    'demo': [],
    'data' : [
        'security/ir.model.access.csv',
        'account_bank_statement_view.xml',
        'account_bank_statement_report.xml',
        'wizard/confirm_statement_line_wizard.xml',
        'wizard/cancel_statement_line_wizard.xml',
        'data/account_bank_statement_extensions_data.xml',
    ],
    'auto_install': False,
    'installable': True,
}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
