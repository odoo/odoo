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
    "name" : "Authenticate users with LDAP server",
    "version" : "1.0",
    "depends" : ["base"],
    "images" : ["images/ldap_configuration.jpeg"],
    "author" : "OpenERP SA",
    'complexity': "easy",
    "description": """
Adds support for authentication by LDAP server.
===============================================
This module allows users to login with their LDAP username and
password, and will automatically create OpenERP users for them
on the fly.

**Note**: This module only work on servers who have Python's
``ldap`` module installed.

Configuration
+++++++++++++
After installing this module, you need to configure the LDAP
parameters in the Configuration tab of the Company details.
Different companies may have different LDAP servers, as long
as they have unique usernames (usernames need to be unique in
OpenERP, even across multiple companies).

Anonymous LDAP binding is also supported (for LDAP servers
that allow it), by simpling keeping the LDAP user and password
empty in the LDAP configuration. This does **not** allow
anonymous authentication for users, it is only for the master
LDAP account that is used to verify if a user exists before
attempting to authenticate it.

Security Considerations
+++++++++++++++++++++++
Users' LDAP passwords are never stored in the OpenERP database,
the LDAP server is queried whenever a user needs to be
authenticated. No duplication of the password occurs, and
passwords are managed in one place only.

OpenERP does not manage password changes in the LDAP, so
any change of password should be conducted by other means
in the LDAP directory directly (for LDAP users).

It is also possible to have local OpenERP users in the
database along with LDAP-authenticated users (the Administrator
account is one obvious example).

Here is how it works:

  * The system first attempts to authenticate users against
    the local OpenERP database ;
  * if this authentication fails (for example because the
    user has no local password), the system then attempts
    to authenticate against LDAP ;

As LDAP users have blank passwords by default in the local
OpenERP database (which means no access), the first step
always fails and the LDAP server is queried to do the
authentication.

User Template
+++++++++++++
In the LDAP configuration on the Company form, it is possible to
select a *User Template*. If set, this user will be used as
template to create the local users whenever someone authenticates
for the first time via LDAP authentication.
This allows pre-setting the default groups and menus of the
first-time users.

**Warning**: if you set a password for the user template,
this password will be assigned as local password for each new
LDAP user, effectively setting a *master password* for these
users (until manually changed). You usually do not want this.
One easy way to setup a template user is to login once with
a valid LDAP user, let OpenERP create a blank local user with the
same login (and a blank password), then rename this new user
to a username that does not exist in LDAP, and setup its
groups the way you want.

Interaction with base_crypt
+++++++++++++++++++++++++++
The base_crypt module is not compatible with this module, and
will disable LDAP authentication if installed at the same time.

    """,


    "website" : "http://www.openerp.com",
    "category" : "Hidden",
    "data" : [
        "users_ldap_view.xml",
        "user_ldap_installer.xml",
    ],
    "active": False,
    "installable": True,
    "certificate" : "001141446349334700221",
    "external_dependencies" : {
        'python' : ['ldap'],
    }
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

