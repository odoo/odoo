# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution	
#    Copyright (C) 2004-2009 Tiny SPRL (<http://tiny.be>). All Rights Reserved
#    $Id$
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

{
    "name": "Portugal - Digital signature",
    "version": "1.00122",
    "category": "Localisation/Account",
    "description": """
        This module allows the OpenERP invoice system to add a digital signature in order to be certified by the
        Portuguese Tax Authority.
    """,
    "author": "Paulino / Sysop",
    "depends": ["l10n_pt_saft"],
    "data": [ 'account_invoice_workflow.xml',  #'invoice_view.xml'
                    ],
    "demo": [],
    "installable": True,
    "active": True,
}

