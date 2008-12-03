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
    "name" : "Base module quality",
    "author" : "Tiny",
    "version" : "1.0",
    "depends" : ["base", "product"],
    "description": "Sample module to check the quality",
    "init_xml" : [],
    "update_xml" : ["base_module_quality_view.xml"],
    "category" : "Tiny Specific Modules/Base module quality",
    "active": False,
    "installable": False
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

