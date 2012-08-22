# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2009 Tiny SPRL (<http://tiny.be>).
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
    'name': 'DB Password Encryption',
    'version': '1.1',
    'author': ['OpenERP SA', 'FS3'],
    'maintainer': 'OpenERP SA',
    'website': 'http://www.openerp.com',
    'category': 'Tools',
    'description': """
Replaces cleartext passwords in the database with a secure hash.
================================================================

For your existing user base, the removal of the cleartext passwords occurs 
immediately when you install base_crypt.

All passwords will be replaced by a secure, salted, cryptographic hash, 
preventing anyone from reading the original password in the database.

After installing this module, it won't be possible to recover a forgotten password 
for your users, the only solution is for an admin to set a new password.

Security Warning:
-----------------
Installing this module does not mean you can ignore other security measures,
as the password is still transmitted unencrypted on the network, unless you
are using a secure protocol such as XML-RPCS or HTTPS.

It also does not protect the rest of the content of the database, which may
contain critical data. Appropriate security measures need to be implemented
by the system administrator in all areas, such as: protection of database
backups, system files, remote shell access, physical server access.

Interaction with LDAP authentication:
-------------------------------------
This module is currently not compatible with the ``user_ldap`` module and
will disable LDAP authentication completely if installed at the same time.
""",
    'depends': ['base'],
    'data': [],
    'auto_install': False,
    'installable': True,
    'certificate': '00721290471310299725',
}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
