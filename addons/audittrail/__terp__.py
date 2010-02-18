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
    'name': 'Audit Trail',
    'version': '1.0',
    'category': 'Generic Modules/Others',
    'description': """Allows the administrator to track every user operations on all objects of the system.
    Subscribe Rules for read, write, create and delete on objects and check logs""",
    'author': 'Tiny',
    'website': 'http://www.openerp.com',
    'depends': ['base'],
    'init_xml': [],
    'update_xml': [
        'audittrail_view.xml',
        'security/ir.model.access.csv',
        'security/audittrail_security.xml'
    ],
    'demo_xml': ['audittrail_demo.xml'],
    'installable': True,
    'active': False,
    'certificate': '0062572348749',
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
