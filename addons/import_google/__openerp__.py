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
    'name': 'Google Import',
    'version': '1.0',
    'category': 'Customer Relationship Management',
    'description': """The module adds google contact in partner address and add google calendar events details in Meeting""",
    'author': 'OpenERP SA',
    'website': 'http://www.openerp.com',
    'depends': ['base', 'import_base', 'google_base_account','crm'],
    'init_xml': [],
    'update_xml': ['security/ir.model.access.csv',
                'sync_google_calendar_view.xml',
                'wizard/import_google_data_view.xml',
                'wizard/google_import_message_view.xml'

               ],
    'demo_xml': [],
    'test': [
             #'test/test_sync_google_contact_import_partner.yml',
            # 'test/test_sync_google_contact_import_address.yml',
             #'test/test_sync_google_calendar.yml',
    ],
    'installable': True,
    'auto_install': False,
    'certificate': '00184345021997',
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
