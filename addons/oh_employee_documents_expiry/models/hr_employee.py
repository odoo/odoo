# -*- coding: utf-8 -*-
#############################################################################
#    A part of Open HRMS Project <https://www.openhrms.com>
#
#    Cybrosys Technologies Pvt. Ltd.
#
#    Copyright (C) 2025-TODAY Cybrosys Technologies(<https://www.cybrosys.com>)
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
from odoo import fields, models, _


class HrEmployee(models.Model):
    """Extended model for managing employee information with document-related
     enhancements."""
    _inherit = 'hr.employee'

    document_count = fields.Integer(compute='_compute_document_count',
                                    string='Documents',
                                    help='Count of documents.')

    def _compute_document_count(self):
        """Get count of documents."""
        for rec in self:
            rec.document_count = self.env[
                'hr.employee.document'].sudo().search_count(
                [('employee_ref_id', '=', rec.id)])

    def action_document_view(self):
        """ Opens a view to list all documents related to the current
         employee."""
        self.ensure_one()
        return {
            'name': _('Documents'),
            'domain': [('employee_ref_id', '=', self.id)],
            'res_model': 'hr.employee.document',
            'type': 'ir.actions.act_window',
            'view_id': False,
            'view_mode': 'list,form',
            'help': _('''<p class="oe_view_nocontent_create">
                           Click to Create for New Documents
                        </p>'''),
            'limit': 80,
            'context': "{'default_employee_ref_id': %s}" % self.id
        }
