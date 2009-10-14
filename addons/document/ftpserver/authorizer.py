# -*- coding: utf-8 -*-
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

import pooler
from service import security

class authorizer:
    read_perms = "elr"
    write_perms = "adfmw"

    def __init__(self):
        self.password = ''

    def validate_authentication(self, username, password):
        """Return True if the supplied username and password match the
        stored credentials."""
        self.password = password
        return True

    def impersonate_user(self, username, password):
        """Impersonate another user (noop).

        It is always called before accessing the filesystem.
        By default it does nothing.  The subclass overriding this
        method is expected to provide a mechanism to change the
        current user.
        """

    def terminate_impersonation(self):
        """Terminate impersonation (noop).

        It is always called after having accessed the filesystem.
        By default it does nothing.  The subclass overriding this
        method is expected to provide a mechanism to switch back
        to the original user.
        """

    def has_user(self, username):
        """Whether the username exists in the virtual users table."""
        if username=='anonymous':
            return False
        return True

    def has_perm(self, username, perm, path=None):
        """Whether the user has permission over path (an absolute
        pathname of a file or a directory).

        Expected perm argument is one of the following letters:
        "elradfmw".
        """
        paths = path.split('/')
        if not len(paths)>2:
            return True
        db_name = paths[1]        
        db,pool = pooler.get_db_and_pool(db_name)
        res = security.login(db_name, username, self.password)
        return bool(res)

    def get_perms(self, username):
        """Return current user permissions."""
        return 'elr'

    def get_home_dir(self, username):
        """Return the user's home directory."""
        return '/'

    def get_msg_login(self, username):
        """Return the user's login message."""
        return 'Welcome on OpenERP document management system.'

    def get_msg_quit(self, username):
        """Return the user's quitting message."""
        return 'Bye.'

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
