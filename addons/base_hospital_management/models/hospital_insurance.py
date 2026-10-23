# -*- coding: utf-8 -*-
################################################################################
#
#    Cybrosys Technologies Pvt. Ltd.
#
#    Copyright (C) 2023-TODAY Cybrosys Technologies(<https://www.cybrosys.com>).
#    Author: Cybrosys Techno Solutions  (odoo@cybrosys.com)
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


class HospitalInsurance(models.Model):
    """Class holding insurance details"""
    _name = 'hospital.insurance'
    _description = 'Hospital Insurance'

    name = fields.Char(string='Provider', help='Name of the insurance provider')
    currency_id = fields.Many2one('res.currency', string='Currency',
                                  help='Currency in which insurance will be '
                                       'calculated',
                                  default=lambda self: self.env.user.company_id
                                  .currency_id.id,
                                  required=True)
    total_coverage = fields.Monetary(string='Total Coverage',
                                     help='Total coverage of the insurance')
