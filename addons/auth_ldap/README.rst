Adds support for authentication by LDAP server.
===============================================
This module allows users to login with their LDAP username and password, and
will automatically create Odoo users for them on the fly.

**Note:** This module only work on servers who have Python's ``ldap`` module installed.

Configuration:
--------------
After installing this module, you need to configure the LDAP parameters in the
General Settings menu. Different companies may have different
LDAP servers, as long as they have unique usernames (usernames need to be unique
in Odoo, even across multiple companies).

Anonymous LDAP binding is also supported (for LDAP servers that allow it), by
simply keeping the LDAP user and password empty in the LDAP configuration.
This does not allow anonymous authentication for users, it is only for the master
LDAP account that is used to verify if a user exists before attempting to
authenticate it.

Securing the connection with STARTTLS is available for LDAP servers supporting
it, by enabling the TLS option in the LDAP configuration.

For further options configuring the LDAP settings, refer to the ldap.conf
manpage: manpage:`ldap.conf(5)`.

Security Considerations:
------------------------
Users' LDAP passwords are never stored in the Odoo database, the LDAP server
is queried whenever a user needs to be authenticated. No duplication of the
password occurs, and passwords are managed in one place only.

Odoo does not manage password changes in the LDAP, so any change of password
should be conducted by other means in the LDAP directory directly (for LDAP users).

It is also possible to have local Odoo users in the database along with
LDAP-authenticated users (the Administrator account is one obvious example).

Here is how it works:
---------------------
    * The system first attempts to authenticate users against the local Odoo
      database;
    * if this authentication fails (for example because the user has no local
      password), the system then attempts to authenticate against LDAP;

As LDAP users have blank passwords by default in the local Odoo database
(which means no access), the first step always fails and the LDAP server is
queried to do the authentication.

Enabling STARTTLS ensures that the authentication query to the LDAP server is
encrypted.

User Template:
--------------
In the LDAP configuration on the General Settings, it is possible to select a *User
Template*. If set, this user will be used as template to create the local users
whenever someone authenticates for the first time via LDAP authentication. This
allows pre-setting the default groups and menus of the first-time users.

**Warning:** if you set a password for the user template, this password will be
         assigned as local password for each new LDAP user, effectively setting
         a *master password* for these users (until manually changed). You
         usually do not want this. One easy way to setup a template user is to
         login once with a valid LDAP user, let Odoo create a blank local
         user with the same login (and a blank password), then rename this new
         user to a username that does not exist in LDAP, and setup its groups
