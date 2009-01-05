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
    "name" : "Human Resources Contracts",
    "version" : "1.0",
    "author" : "Tiny",
    "category" : "Generic Modules/Human Resources",
    "website" : "http://www.openerp.com",
    "depends" : ["hr"],
    "module": "",
    "description": """
    Add all information on the employee form to manage contracts:
    * Martial status,
    * Security number,
    * Place of birth, birth date, ...

    You can assign several contracts per employee.
    """,
    "init_xml" : ["hr_contract_data.xml", ],
    "demo_xml" : [],
    "update_xml" : [
        "security/hr_contract_security.xml",
        "security/ir.model.access.csv",
        "hr_contract_view.xml",
    ],
    "active": False,
    "installable": True
}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

