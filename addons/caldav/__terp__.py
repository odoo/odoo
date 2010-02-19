# -*- coding: utf-8 -*-
##############################################################################
#    
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
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
    "name" : "Share Calendar using Caldav", 
    "version" : "1.0", 
    "depends" : [
                    "base", 
                ], 
     'description': """
 Contains basic functionality for caldav system like:  
  - Availabilities of synchronisation using WebDAV
""", 
    "author" : "Tiny", 
    'category': 'Generic Modules/Others', 
    'website': 'http://www.openerp.com', 
    "init_xml" : ["caldav_data.xml"], 
    "demo_xml" : [], 
    "update_xml" : [
                    'security/ir.model.access.csv', 
                    'caldav_wizard.xml', 
                    'caldav_view.xml'
                    ], 
    "installable" : True, 
    "active" : False, 
}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
