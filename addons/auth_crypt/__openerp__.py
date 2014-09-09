# -*- encoding: utf-8 -*-
##############################################################################
#
#    Odoo, Open Source Management Solution
#    Copyright (C) 2004-2014 OpenERP S.A. (<http://odoo.com>).
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
    'name': 'Password Encryption',
    'version': '2.0',
    'author': ['OpenERP SA', 'FS3'],
    'maintainer': 'OpenERP SA',
    'website': 'https://www.odoo.com',
    'category': 'Tools',
    'description': """
Encrypted passwords
===================

Replaces the default password storage with a strong cryptographic
hash.

The key derivation function currently used is RSA Security LLC's
industry-standard ``PKDF2``, in combination with ``SHA512``.
This includes salting and key stretching with several thousands
rounds.

All passwords are encrypted as soon as the module is installed.
This may take a few minutes if there are thousands of users.

Past versions of encrypted passwords will be automatically upgraded
to the current scheme whenever a user authenticates
(``auth_crypt`` was previously using the weaker ``md5crypt`` key
derivation function).

Note: Installing this module permanently prevents user password
recovery and cannot be undone. It is thus recommended to enable
some password reset mechanism for users, such as the one provided
by the ``auth_signup`` module (signup for new users does not
necessarily have to be enabled).

""",
    'depends': ['base'],
    'data': [],
    'auto_install': True,
    'installable': True,
}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
