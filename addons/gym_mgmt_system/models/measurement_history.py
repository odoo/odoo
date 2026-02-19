# -*- coding: utf-8 -*-
#############################################################################
#
#    Cybrosys Technologies Pvt. Ltd.
#
#    Copyright (C) 2023-TODAY Cybrosys Technologies(<https://www.cybrosys.com>)
#    Author: Sahla Sherin(<https://www.cybrosys.com>)
#
#    You can modify it under the terms of the GNU LESSER
#    GENERAL PUBLIC LICENSE (AGPL v3), Version 3.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU LESSER GENERAL PUBLIC LICENSE (AGPL v3) for more details.
#
#    You should have received a copy of the GNU LESSER GENERAL PUBLIC LICENSE
#    (AGPL v3) along with this program.
#    If not, see <http://www.gnu.org/licenses/>.
#
#############################################################################
from odoo import api, fields, models


class MeasurementHistory(models.Model):
    """This model used for measurement history."""
    _name = "measurement.history"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _description = "Measurement History"
    _rec_name = "gender"

    def _get_default_weight_uom(self):
        """ to get default weight uom """
        return self.env[
            'product.template']._get_weight_uom_name_from_ir_config_parameter()

    member_id = fields.Many2one('res.partner', string='Member',
                                tracking=True, required=True,
                                domain="[('gym_member', '!=',False)]",
                                help='Name of the member')
    gender = fields.Selection([
        ('male', 'Male'),
        ('female', 'Female'),
        ('other', 'Other'),
    ], string="Gender", required=True, help='Select the gender')
    age = fields.Integer(string='Age', tracking=True, required=True,
                         help='Enter the age')
    weight = fields.Float(
        'Weight', digits='Stock Weight', store=True,
        help='define the your weight')
    weight_uom_name = fields.Char(string='Weight unit of measure label',
                                  default=_get_default_weight_uom,
                                  help='weight uom ')
    height = fields.Float(
        'Height', digits='Stock Height', store=True, help='Define your '
                                                          'height')
    height_uom_name = fields.Char(string='height unit of measure label',
                                  default='cm', help='height uom')
    bmi = fields.Float(string='BMI', store=True,
                       compute='_compute_display_name', help='Calculate BMI')
    bmr = fields.Float(string='BMR', store=True,
                       compute='_compute_display_name',
                       help='Calculate BMR')
    neck = fields.Float(string='neck', store=True, help='The length of neck')
    biceps = fields.Float(string='Biceps', store=True,
                          help='The length of biceps')
    calf = fields.Float(string='Calf', store=True, help='The length of calf')
    hips = fields.Float(string='Hips', store=True, help='The length of hips')
    chest = fields.Float(string='Chest', store=True,
                         help='The length of chest')
    waist = fields.Float(string='Waist', store=True,
                         help='The length of waist')
    thighs = fields.Float(string='Thighs', store=True,
                          help='The length of thighs')
    date = fields.Date(string='Date',
                       help='Date from which measurement active.')
    company_id = fields.Many2one('res.company', string='Company',
                                 default=lambda self: self.env.company,
                                 help="This field hold the company id")

    @api.depends('weight', 'height')
    def _compute_display_name(self):
        """Based on weight and height ,calculate the bmi and bmr"""
        self.bmi = self.bmr = 0
        self.display_name = self.member_id.name
        if self.weight and self.height:
            self.bmi = (self.weight / self.height / self.height) * 10000
            if self.gender == "male":
                self.bmr = 66.47 + (13.75 * self.weight) + \
                           (5.003 * self.height) - (6.755 * self.age)
            if self.gender == "female":
                self.bmr = 655.1 + (9.563 * self.weight) + \
                           (1.85 * self.height) - (6.755 * self.age)
        else:
            self.bmi = 1
            self.bmr = 1
            self.display_name = self.member_id.name
