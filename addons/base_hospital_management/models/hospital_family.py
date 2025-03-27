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


class HospitalFamily(models.Model):
    """Class holding hospital family details"""
    _name = 'hospital.family'
    _description = 'Hospital Family'

    name = fields.Char(string="Name", help='Name of family member')
    relation = fields.Char(string="Relation", help='Relation with the patient')
    age = fields.Integer(string="Age", help='Age of family member')
    deceased = fields.Selection([('yes', 'Yes'), ('no', 'NO')],
                                string="Diseased", help='Specify whether the '
                                                        'family member is '
                                                        'alive or not')
    family_id = fields.Many2one('res.partner',
                                string="Family ID", help='Choose the family '
                                                         'member')
