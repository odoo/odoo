# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2010-Today OpenERP SA (<http://www.openerp.com>)
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>
#
##############################################################################

from openerp.osv import osv


class mail_message(osv.Model):
    _name = 'mail.message'
    _inherit = 'mail.message'

    def check_related_document(self, cr, uid, model_obj, mids, operation, context=None):
        """If the user posting the message to an employee  is an employee, only
        the read access are checked"""

        if model_obj._name == 'hr.employee':
            employee_ids = model_obj.search(cr, uid, [('user_id', '=', uid)], context=context)
            if employee_ids:
                model_obj.check_access_rights(cr, uid, 'read')
                model_obj.check_access_rule(cr, uid, mids, 'read', context=context)
                return

        super(mail_message, self).check_related_document(cr, uid, model_obj, mids, operation, context)
