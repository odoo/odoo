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


class PharmacyMedicine(models.Model):
    """Class holding Pharmacy medicine details"""
    _name = 'pharmacy.medicine'
    _description = 'pharmacy Medicine'
    _rec_name = 'product_id'

    product_id = fields.Many2one('product.template',
                                 string='Medicine',
                                 help='Name of medicine',
                                 domain="[('medicine_ok', '=', True)]")
    pharmacy_id = fields.Many2one('hospital.pharmacy',
                                  string='Pharmacy',
                                  help='Name of pharmacy')
    qty_available = fields.Float(related='product_id.qty_available',
                                 string='Available Quantity',
                                 help='The quantity of product available')
    list_price = fields.Float(related='product_id.list_price', string='Price',
                              help='Price of the medicine')
