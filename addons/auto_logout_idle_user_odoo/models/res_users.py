# -*- coding: utf-8 -*-
################################################################################
#
#    Cybrosys Technologies Pvt. Ltd.
#
#    Copyright (C) 2023-TODAY Cybrosys Technologies(<https://www.cybrosys.com>).
#    Author: Yadhukrishnan K (odoo@cybrosys.com)
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
################################################################################
from odoo import fields, models


class Users(models.Model):
    """ Inherit and adding some fields to the 'res.users'"""
    _inherit = "res.users"

    enable_idle = fields.Boolean(string="Enable Idle Time",
                                 help="Enable Idle Timer")
    idle_time = fields.Integer(string="Idle Time (In minutes)", default=10,
                               help="Set Idle Time For theis User")
    # SQL constraints
    _sql_constraints = [
        ('positive_idle_time', 'CHECK(idle_time >= 1)',
         'Idle Time should be a positive number.'),
    ]
