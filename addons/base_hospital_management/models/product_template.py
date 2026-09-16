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
from odoo import api, fields, models


class ProductTemplate(models.Model):
    """Inherited to add more fields and functions"""
    _inherit = 'product.template'

    medicine_ok = fields.Boolean(string='Medicine', help='True for medicines')
    vaccine_ok = fields.Boolean(string="Vaccine", help='True for vaccines')
    pharmacy_id = fields.Many2one('hospital.pharmacy',
                                  string='Pharmacy',
                                  help='Name of the pharmacy')
    medicine_brand_id = fields.Many2one('medicine.brand',
                                        string='Brand',
                                        help='Indicates the brand of medicine '
                                             'or vaccine')

    @api.model
    def action_get_medicine_data(self):
        """Returns medicine list to the pharmacy dashboard"""
        medicines = []
        for rec in self.env['product.template'].sudo().search(
                [('medicine_ok', '=', True)]):
            medicines.append(
                [rec.name, rec.list_price, rec.qty_available, rec.image_1920])
        values = {
            'medicine': medicines,
        }
        return values

    @api.model
    def action_get_vaccine_data(self):
        """Returns vaccine list to the pharmacy dashboard"""
        vaccines = []
        for rec in self.env['product.template'].sudo().search(
                [('vaccine_ok', '=', True)]):
            vaccines.append(
                [rec.name, rec.list_price, rec.qty_available, rec.image_1920])
        values = {
            'medicine': vaccines,
        }
        return values
