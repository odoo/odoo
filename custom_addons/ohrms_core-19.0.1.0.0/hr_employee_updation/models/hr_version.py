# -*- coding: utf-8 -*-
#############################################################################
#    A part of OpenHRMS Project <https://www.openhrms.com>
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
from odoo import api, fields, models


class HrVersion(models.Model):
    """This class extends the 'hr.contract' model to add a custom 'notice_days'
     field. The 'notice_days' field is used to store the notice period for HR
     contracts."""
    _inherit = 'hr.version'

    notice_days = fields.Integer(
        string="Notice Period",
        compute="_compute_notice_days",
        store=False,  # keep False if you want it dynamic
        help="Number of days required for notice before termination."
    )

    @api.depends_context('uid')
    def _compute_notice_days(self):
        """Compute notice period from company's setting"""
        for record in self:
            record.notice_days = record.company_id.contract_expiration_notice_period or 0
