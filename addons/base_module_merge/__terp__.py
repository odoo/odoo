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
    "name" : "Module Merger",
    "version" : "1.0",
    "author" : "Tiny",
    "website" : "http://www.openerp.com",
    "category" : "Generic Modules/Base",
    "description": """
    * The wizard asks a many2many of modules
    * And then generate a module which is the merge of all selected modules
    * The new module is provided as a .zip file

    The merge will works in all situations:
    * Merging all .py files with the same name in the new module
    * merging all .xml files and take care of id's.
    """,
    "depends" : ["base"],
    "init_xml" : [ ],
    "demo_xml" : [ ],
    "update_xml" : [ "base_module_merge_wizard.xml" ],
    "installable": True
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

