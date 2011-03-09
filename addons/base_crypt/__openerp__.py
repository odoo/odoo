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
    "name" : "Base - Password Encryption",
    "version" : "1.1",
    "author" : "FS3 & OpenERP SA",
    "maintainer" : "OpenERP SA",
    "website" : "http://www.openerp.com",
    "category" : "Tools",
    "description": """This module replaces the cleartext password in the database with a password hash,
preventing anyone from reading the original password.
For your existing user base, the removal of the cleartext passwords occurs the first time
a user logs into the database, after installing base_crypt.
After installing this module it won't be possible to recover a forgotten password for your
users, the only solution is for an admin to set a new password.

Note: installing this module does not mean you can ignore basic security measures,
as the password is still transmitted unencrypted on the network (by the client),
unless you are using a secure protocol such as XML-RPCS.
                    """,
    "depends" : ["base"],
    "data" : [],
    "active": False,
    "installable": True,
    "certificate" : "00721290471310299725",
}
