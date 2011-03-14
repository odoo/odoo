# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2009 Tiny SPRL (<http://tiny.be>). All Rights Reserved
#    $Id$
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
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
from osv import osv, fields
from tools.translate import _

class hired_employee(osv.osv_memory):
    _name = 'hired.employee'
    _description = 'Create Employee'

    def case_close(self, cr, uid,ids, context=None):
        """
        @param self: The object pointer
        @param cr: the current row, from the database cursor,
        @param uid: the current user’s ID for security checks,
        @param ids: List of case's Ids
        @param *args: Give Tuple Value
        """
        if context is None:
            context = {}
        self.pool.get('hr.applicant').case_close(cr, uid,context.get('active_ids',[]))
        return {}

    def case_close_with_emp(self, cr, uid,ids, context=None):
        """
        @param self: The object pointer
        @param cr: the current row, from the database cursor,
        @param uid: the current user’s ID for security checks,
        @param ids: List of case's Ids
        """
        if context is None:
            context = {}
        self.pool.get('hr.applicant').case_close_with_emp(cr, uid,context.get('active_ids', []))
        return {}

hired_employee()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
