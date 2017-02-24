# -*- coding: utf-8 -*-
###############################################################################
#
#    Tech-Receptives Solutions Pvt. Ltd.
#    Copyright (C) 2009-TODAY Tech-Receptives(<http://www.techreceptives.com>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Lesser General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Lesser General Public License for more details.
#
#    You should have received a copy of the GNU Lesser General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
###############################################################################

from openerp import models, fields, api


class WizardOpFacultyEmployee(models.TransientModel):
    _name = 'wizard.op.faculty.employee'
    _description = "Create Employee and User of Faculty"

    user_boolean = fields.Boolean("Want to create user too ?", default=True)

    @api.one
    def create_employee(self):
        active_id = self.env.context.get('active_ids', []) or []
        record = self.env['op.faculty'].browse(active_id)
        record.create_employee()
        if self.user_boolean and not record.user_id:
            user_group = self.env.ref('openeducat_core.group_op_faculty')
            self.env['res.users'].create_user(record, user_group)


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
