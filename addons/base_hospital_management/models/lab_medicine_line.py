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


class LabMedicineLine(models.Model):
    """Class holding Lab medicines"""
    _name = 'lab.medicine.line'
    _description = 'Lab Medicine Line'

    lab_test_id = fields.Many2one('patient.lab.test',
                                  string='Lab Test Line',
                                  help='Lab test corresponds to the medicine')
    test_id = fields.Many2one('lab.test', string='Test',
                              help='Test corresponds to medicine')
    medicine_id = fields.Many2one('product.template',
                                  domain="['|', ('medicine_ok', '=', True),"
                                         "('vaccine_ok', '=', True)"
                                         "]", required=True, string='Medicine',
                                  help='Medicine for the lab test')
    quantity = fields.Integer(string='Quantity', default=1,
                              help='Quantity of medicine')
    qty_available = fields.Float(string='Available', help='Available quantity',
                                 related='medicine_id.qty_available')
    price = fields.Float(string='Price', help='Price for the medicine',
                         related='medicine_id.list_price')
    sub_total = fields.Float(string='Subtotal',
                             help='Total cost of the medicine',
                             compute='_compute_sub_total')

    @api.depends('quantity', 'price')
    def _compute_sub_total(self):
        """Method for computing total amount"""
        for rec in self:
            rec.sub_total = rec.price * rec.quantity
