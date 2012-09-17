#!/usr/bin/env python
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2010-2012 OpenERP s.a. (<http://openerp.com>).
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

KEY_LENGTH = 16

SREG2AX = {     # from http://www.axschema.org/types/#sreg
    'nickname': 'http://axschema.org/namePerson/friendly',
    'email': 'http://axschema.org/contact/email',
    'fullname': 'http://axschema.org/namePerson',
    'dob': 'http://axschema.org/birthDate',
    'gender': 'http://axschema.org/person/gender',
    'postcode': 'http://axschema.org/contact/postalCode/home',
    'country': 'http://axschema.org/contact/country/home',
    'language': 'http://axschema.org/pref/language',
    'timezone': 'http://axschema.org/pref/timezone',
}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
