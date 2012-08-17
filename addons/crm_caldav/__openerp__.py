
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
    'name': 'Meetings Synchronization',
    'version': '1.1',
    'category': 'Customer Relationship Management',
    'description': """
Caldav features in Meeting.
===========================

    * Share meeting with other calendar clients like sunbird
""",
    'author': 'OpenERP SA',
    'website': 'http://www.openerp.com',
    'depends': ['caldav', 'crm' ],
    'data': [
                'crm_caldav_data.xml',
                'crm_caldav_setup.xml',
                ],

    'data': ['crm_caldav_view.xml'],
    'demo': [],
    'installable': True,
    'auto_install': False,
    'certificate' : '001088048737252670109',
    'images': ['images/caldav_browse_step1.jpeg','images/caldav_browse_step2.jpeg'],
}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
