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
    'name': 'Integrated Document Management System',
    'version': '1.0',
    'category': 'Generic Modules/Others',
    'description': """This is a complete document management system:
    * FTP Interface
    * User Authentication
    * Document Indexation

    ATTENTION: 
    - When you install this module in a running company that have already PDF files stored into the database, 
      you will lose them all. 
    - After installing this module PDF's are not longer stored into the database, 
      but in the servers rootpad like /server/bin/filestore.
""",
    'author': 'Tiny',
    'website': 'http://www.openerp.com',
    'depends': ['base', 'process'],
    'init_xml': ['document_data.xml', 'document_demo.xml'],
    'update_xml': [
        'document_view.xml',
        'document_data.xml',
        'security/document_security.xml',
        'security/ir.model.access.csv'
    ],
    'demo_xml': [],
    'installable': True,
    'active': False,
    'certificate': '0070515416461',
}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
