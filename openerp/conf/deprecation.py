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

In a perfect world, all these variables are set to False, the corresponding
code removed, and thus these variables made unnecessary.
"""

# If True, the Python modules inside the openerp namespace are made available
# without the 'openerp.' prefix. E.g. openerp.osv.osv and osv.osv refer to the
# same module.
# Introduced around 2011.02.
# Change to False around 2013.02.
open_openerp_namespace = False

# If True, openerp.netsvc.LocalService() can be used to lookup reports or to
# access openerp.workflow.
# Introduced around 2013.03.
# Among the related code:
# - The openerp.netsvc.LocalService() function.
# - The openerp.report.interface.report_int._reports dictionary.
# - The register attribute in openerp.report.interface.report_int (and in its
# - auto column in ir.actions.report.xml.
# inheriting classes).
allow_local_service = True

# Applies for the register attribute in openerp.report.interface.report_int.
# See comments for allow_local_service above.
# Introduced around 2013.03.
allow_report_int_registration = True

# If True, the functions in openerp.pooler can be used.
# Introduced around 2013.03 (actually they are deprecated since much longer
# but no warning was dispayed in the logs).
openerp_pooler = True

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
