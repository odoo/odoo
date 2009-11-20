# -*- coding: utf-8 -*-
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
    "name" : "Accounting Voucher Entries",
    "version" : "1.0",
    "author" : 'Tiny & Axelor',
    "description": """
    India Accounting module includes all the basic requirenment of 
    Basic Accounting, like
    * Bank Payment, Receipt
    * Cash Payent, Receipt
    """,
    "category" : "Generic Modules/Indian Accounting",
    "website" : "http://tinyerp.com",
    "depends" : ["base", "account"],
    "init_xml" : [
    ],
    
    "demo_xml" : [
    ],
    
    "update_xml" : [
        "voucher_sequence.xml",
        "account_view.xml",
        "account_report.xml",
        "voucher_wizard.xml",
        "voucher_view.xml",
    ],
    'certificate': '0037580727101',
    "active": False,
    "installable": True,
}
