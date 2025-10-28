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
from odoo import fields, models


class HrContractAdvantageTemplate(models.Model):
    """Create a new model for adding fields."""
    _name = 'hr.contract.advantage.template'
    _description = "Employee's Advantage on Contract"

    name = fields.Char(string='Name', required=True,
                       help="Name for Employee's Advantage on Contract")
    code = fields.Char(string='Code', required=True,
                       help="Code for Employee's Advantage on Contract")
    lower_bound = fields.Float(string='Lower Bound',
                               help="Lower bound authorized by the employer"
                                    "for this advantage")
    upper_bound = fields.Float(string='Upper Bound',
                               help="Upper bound authorized by the employer"
                                    "for this advantage")
    default_value = fields.Float(string="Default Value",
                                 help='Default value for this advantage')
