# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
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

from openerp import models, fields, api, _

class res_company(models.Model):
    _inherit = 'res.company'

    project_time_mode_id = fields.Many2one('product.uom', string='Project Time Unit',
        help='This will set the unit of measure used in projects and tasks.\n' \
"If you use the timesheet linked to projects (project_timesheet module), don't " \
"forget to setup the right unit of measure in your employees.",
    )


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
