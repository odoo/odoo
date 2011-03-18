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
    "name": "Decimal Precision Configuration",
    "description": """Configure your Price Accuracy according to your needs
This module allows to configure the price accuracy you need for different kind
of usage: accounting, sales, purchases, ...

The decimal precision is configured per company.
""",
    "author": "OpenERP SA",
    "version": "0.1",
    "depends": ["base"],
    "category" : "Tools",
    "init_xml": [],
    "update_xml": [
        'decimal_precision_view.xml',
        'security/ir.model.access.csv',
    ],
    "demo_xml": [],
    "installable": True,
    "certificate" : "001307317809612974621",
}


