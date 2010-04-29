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
    'name': 'Email Gateway System',
    'version': '1.0',
    'category': 'Generic Modules/Mail Service',
    'description': """The generic email gateway system allows to send and receive emails
    * IMAP / IMAP with SSL
    * POP / POP with SSL
    * SMTP / SMTP with TLS
    * ACL basd access polocy 
    * Queing and History for Emails
    * Easy Integration with any Module""",
    'author': 'Tiny',
    'website': 'http://www.openerp.com',
    'depends': ['smtpclient'],
    'init_xml': [],
    'update_xml': [
        
    ],
    'demo_xml': [],
    'installable': True,
    'active': False,
    'certificate': None,
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
