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

""" Regroup variables for deprecated features.

To keep the OpenERP server backward compatible with older modules, some
additional code is needed throughout the core library. This module keeps
track of those specific measures by providing variables that can be unset
by the user to check if her code is future proof.

"""

# If True, the Python modules inside the openerp namespace are made available
# without the 'openerp.' prefix. E.g. openerp.osv.osv and osv.osv refer to the
# same module.
# Introduced around 2011.02.
open_openerp_namespace = True

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
