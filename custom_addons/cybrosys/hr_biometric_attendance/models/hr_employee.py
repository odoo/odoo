# -*- coding: utf-8 -*-
################################################################################
#
#    Cybrosys Technologies Pvt. Ltd.
#
#    Copyright (C) 2025-TODAY Cybrosys Technologies(<https://www.cybrosys.com>).
#    Author: Cybrosys Techno Solutions (odoo@cybrosys.com)
#
#    You can modify it under the terms of the GNU AFFERO
#    GENERAL PUBLIC LICENSE (AGPL v3), Version 3.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU AFFERO GENERAL PUBLIC LICENSE (AGPL v3) for more details.
#
#    You should have received a copy of the GNU AFFERO GENERAL PUBLIC LICENSE
#    (AGPL v3) along with this program.
#    If not, see <http://www.gnu.org/licenses/>.
#
################################################################################
from odoo import fields, models


class HrEmployee(models.Model):
    """Inherit hr.employee to add biometric device ID"""
    _inherit = 'hr.employee'

    biometric_user_id = fields.Integer(
        string='Biometric User ID',
        groups='hr.group_hr_user',
        help='ID from ZKTeco device. Must match the user ID on the '
             'biometric device for attendance to be linked.',
        copy=False,
    )

    device_id = fields.Many2one(
        'biometric.device.details',
        string='Biometric Device',
        groups='hr.group_hr_user',
        copy=False,
        readonly=True,
        help='The biometric device this employee is registered on',
    )



