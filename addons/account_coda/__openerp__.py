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
    "name"      : "Account CODA - import bank statements from coda file",
    "version"   : "1.0",
    "author"    : "OpenERP SA",
    "category"  : "Finance",
    'complexity': "normal",
    "description": """
Module provides functionality to import bank statements from coda files.
========================================================================

Contains a wizard to import coda statements and maintains logs for the same.
    """,
    "images"   : ["images/coda_logs.jpeg","images/import_coda_logs.jpeg"],
    "depends"   : ["account_voucher"],
    "demo_xml"  : [],
    "init_xml"  : [],
    "update_xml": ["security/ir.model.access.csv",
                    "security/account_security.xml",
                    "wizard/account_coda_import.xml",
                    "account_coda_view.xml"],
    "active"    : False,
    "installable" : True,
    "certificate" : "001237207321716002029",

}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

