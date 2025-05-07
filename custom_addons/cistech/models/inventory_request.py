# -*- coding: utf-8 -*-
#############################################################################
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
from odoo import api, fields, models


class InventoryRequest(models.Model):
    """Creating class inventoryRequest for requesting products"""
    _name = 'inventory.request'
    _description = "Inventory Request"

    name = fields.Char(string='Title', required=True, help='Name of the '
                                                           'request')
    product_id = fields.Many2one('product.template',
                                 string='Product', help='Product name',
                                 required=True)
    seller_id = fields.Many2one(related='product_id.seller_id', help='Seller',
                                string='Seller')
    qty_new = fields.Integer(string='New quantity',
                             help='New quantity on hand',
                             required=True)
    location_id = fields.Many2one('stock.location',
                                  string='Location', help='Location',
                                  required=True)
    date = fields.Datetime(string='Created Date', help='Date',
                           default=fields.Datetime.today())
    note = fields.Text(string='Note', help='Note')
    state = fields.Selection(
        selection=[('Draft', 'Draft'), ('Requested', 'Requested'),
                   ('Approved', 'Approved'), ('Rejected', 'Rejected')],
        string='Inventory Req Status', group_expand='_group_expand_states',
        help="For adding state", default='Draft', track_visibility='always',
        readonly=True)

    @api.onchange('name')
    def _onchange_name(self):
        """ Fetch location details from settings and search that id """
        id_in_location_frm_settings = self.env[
            'ir.config_parameter'].sudo().get_param(
            'multi_vendor_marketplace.seller_location_id')
        id_in_location = self.env['stock.location'].browse(id_in_location_frm_settings)
        self.location_id = id_in_location.id

    def _group_expand_states(self):
        """Expands the selection options for the 'state' field in a group-by
        operation."""
        return [key for key, val in type(self).state.selection]

    def approve_request(self):
        """ Product request approve """
        self.state = 'Approved'
        product_ids = self.env['product.template'].browse(self.product_id.id)
        products_ids = self.env['product.product'].browse(product_ids.id)
        product_ids.qty_available = product_ids.qty_available + self.qty_new
        self.env['stock.quant'].with_context(inventory_mode=True).create(
            [{'product_id': products_ids.id,
              'inventory_quantity': product_ids.qty_available,
              'location_id': self.location_id.id,
              }]).action_apply_inventory()

    def reject_request(self):
        """ Reject seller new product """
        self.state = 'Rejected'

    def request(self):
        """ Used in seller for request to approve new product for selling """
        if self.env['ir.config_parameter'].sudo().get_param(
                'multi_vendor_marketplace.quantity_approval'):
            self.approve_request()
        else:
            self.state = 'Requested'
