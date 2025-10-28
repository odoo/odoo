# -*- coding: utf-8 -*-
#############################################################################
#    A part of Open HRMS Project <https://www.openhrms.com>
#
#    Cybrosys Technologies Pvt. Ltd.
#
#    Copyright (C) 2024-TODAY Cybrosys Technologies(<https://www.cybrosys.com>)
#    Author: Cybrosys Techno Solutions(<https://www.cybrosys.com>)
#
#    You can modify it under the terms of the GNU LESSER
#    GENERAL PUBLIC LICENSE (LGPL v3), Version 3.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU LESSER GENERAL PUBLIC LICENSE (LGPL v3) for more details.
#
#    You should have received a copy of the GNU LESSER GENERAL PUBLIC LICENSE
#    (LGPL v3) along with this program.
#    If not, see <http://www.gnu.org/licenses/>.
#
#############################################################################
from odoo import models, api

class HrVersion(models.Model):
    _inherit = 'hr.version'

    @api.model
    def get_hr_version_list_view_id(self):
        """Return the ID of the hr.version list/tree view for dashboard actions"""
        view = self.env.ref('hr.hr_version_list_view', raise_if_not_found=False)
        if view:
            return view.id
        view = self.env['ir.ui.view'].search([
            ('model', '=', 'hr.version'),
            ('type', '=', 'list')
        ], limit=1)
        return view.id if view else False