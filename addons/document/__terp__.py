# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution	
#    Copyright (C) 2004-2008 Tiny SPRL (<http://tiny.be>). All Rights Reserved
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
    "name" : "Integrated Document Management System",
    "version" : "1.0",
    "author" : "Tiny",
    "category" : "Generic Modules/Others",
    "website": "http://www.tinyerp.com",
    "description": """This is a complete document management system:
    * FTP Interface
    * User Authentification
    * Document Indexation
""",
    "depends" : ["base","process"],
    "init_xml" : [
        "document_data.xml",
        "document_demo.xml"
    ],
    "update_xml" : [
        "document_view.xml",
        "document_data.xml",
        "security/document_security.xml",
        "security/ir.model.access.csv",
    ],
    "demo_xml" : [],
    "active": False,
    "installable": True
}
