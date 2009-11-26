# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#
#    Copyright (C) P. Christeas, 2009, all rights reserved
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
	"name" : "Document Protocol",
	"version" : "0.1",
	"author"  : "P. Christeas" ,
	"website" : "http://openerp.hellug.gr",
        "description"  : """ Protocol functionality for document management.
	
	With this, documents can take a protocol number, and be locked down with it.
	 """,
	"depends" : ["base","document", "document_lock"],
	"init_xml" : [],
	"demo_xml" : [],
	"update_xml" : ["document_protocol.xml"],
	"active": False,
	"installable": True
}
