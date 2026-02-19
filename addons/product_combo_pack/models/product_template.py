# -*- coding: utf-8 -*-
################################################################################
#
#    Cybrosys Technologies Pvt. Ltd.
#
#    Copyright (C) 2024-TODAY Cybrosys Technologies (<https://www.cybrosys.com>)
#    Author: Jumana jabin MP (odoo@cybrosys.com)
#
#    This program is free software: you can modify
#    it under the terms of the GNU Affero General Public License (AGPL) as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <https://www.gnu.org/licenses/>.
#
################################################################################
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class ProductPack(models.Model):
    """Model for extending the product template to include
     pack-related fields."""
    _inherit = 'product.template'

    def default_pack_location(self):
        """ Get the default pack location for the current company."""
        company_user = self.env.company
        warehouse = self.env['stock.warehouse'].search([(
            'company_id', '=', company_user.id)], limit=1)
        if warehouse:
            return warehouse.lot_stock_id.id

    is_pack = fields.Boolean('Is a Pack', help='Indicates whether the'
                                               ' product is a pack or not.')
    pack_price = fields.Integer(string="Pack Price", compute='set_pack_price',
                                store=True,
                                help='The calculated price of the pack.')
    pack_products_ids = fields.One2many('pack.products', 'product_tmpl_id',
                                        string='Pack Products', copy=True,
                                        help='The list of products included '
                                             'in the pack.')
    pack_quantity = fields.Integer('Pack Quantity',
                                   help='The quantity of the product'
                                        ' in the pack.')
    pack_location_id = fields.Many2one('stock.location',
                                       domain=[('usage', 'in',
                                                ['internal', 'transit'])],
                                       default=default_pack_location,
                                       string='Pack Location',
                                       help='The default location for the pack.')

    @api.depends('pack_products_ids', 'pack_products_ids.price')
    def set_pack_price(self):
        """Compute the pack price based on the prices of the pack products."""
        price = 0
        for record in self:
            for line in record.pack_products_ids:
                price = price + line.price
            record.pack_price = price

    @api.model
    def create(self, values):
        """Override the create method to add validation for pack products."""
        if values.get('is_pack', False):
            if not values.get('pack_products_ids', []):
                raise UserError(_(
                    'You need to add at-least one product in the Pack...!'))
        return super(ProductPack, self).create(values)

    def write(self, values):
        """Override the write method to add validation for pack products."""
        super(ProductPack, self).write(values)
        for rec in self:
            if rec.is_pack:
                if not rec.pack_products_ids:
                    raise UserError(_(
                        'You need to add at least one product in the Pack...!'))

    def update_price_product(self):
        """Update the list price of the product with the pack price."""
        self.list_price = self.pack_price

    def get_quantity(self):
        """Calculate the pack quantity based on the availability of
        pack products."""
        total_quantity = 1
        flag = 1
        max_iterations = 1000
        while flag and total_quantity < max_iterations:
            for line in self.pack_products_ids:
                if line.qty_available >= line.quantity * total_quantity:
                    continue
                else:
                    if line.product_id.type != 'product':
                        continue
                    flag = 0
                    break
            if flag:
                total_quantity += 1
        self.pack_quantity = total_quantity - 1

    def update_quantity(self):
        """Update the pack quantity in the specified pack location."""
        company_user = self.env.company
        product_id = len(
            self.product_variant_ids) == 1 and self.product_variant_id.id
        location_id = self.pack_location_id.id
        if not location_id:
            warehouse = self.env['stock.warehouse'].search([(
                'company_id', '=', company_user.id)], limit=1)
            location_id = warehouse.lot_stock_id.id
            if not location_id:
                raise UserError(_(
                    'You need to select the location to update the pack quantity...!'))
        self.env['stock.quant'].with_context(inventory_mode=True).sudo().create(
            {
                'product_id': product_id,
                'location_id': location_id,
                'inventory_quantity': self.pack_quantity,
            })

    @api.onchange('pack_location_id')
    def change_quantity_based_on_location(self):
        """Update the total available quantity of pack products based
        on the selected pack location."""
        for line in self.pack_products_ids:
            stock_quant = self.env['stock.quant'].search(
                [('product_id', '=', line.product_id.id), (
                    'location_id', '=', self.pack_location_id.id)])
            if stock_quant:
                line.total_available_quantity = stock_quant.quantity
            else:
                line.total_available_quantity = stock_quant.quantity
