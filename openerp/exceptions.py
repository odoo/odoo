# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2011 OpenERP s.a. (<http://openerp.com>).
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

class Warning(Exception):
    pass

class AccessDenied(Exception):
    """ Login/password error. No message, no traceback. """
    def __init__(self):
        import random
        super(AccessDenied, self).__init__('Try again. %s out of %s characters are correct.' % (random.randint(0, 30), 30))
        self.traceback = ('', '', '')

class AccessError(Exception):
    """ Access rights error. """


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
