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
from odoo import fields, models,_
from odoo.exceptions import UserError


class SellerShop(models.Model):
    """Managing Seller Shops"""
    _name = 'seller.shop'
    _description = "Seller Shop"

    name = fields.Char(string="Name", help="Name of the shop")
    shop_url = fields.Char(string='Shop Url',
                           help="Shop url which can redirect from the website",
                           required=True)
    shop_banner = fields.Char(string="Shop Banner",
                              help="Banner of the shop which can be displayed "
                                   "on the website")
    tag_line = fields.Char(string='Tag Line', help="Tag line for the shop")
    description = fields.Char(string='Description',
                              help="Description for the shop")
    seller_id = fields.Many2one('res.partner', string='Seller',
                                help="Seller name", default=lambda
            self: self.env.user.partner_id.id,
                                domain=[('state', '=', 'Approved')])
    seller_image = fields.Binary(related='seller_id.image_1920',
                                 string="Seller image",
                                 help="Image of the seller")
    address = fields.Text(string='Address', help="Address of the seller")
    phone = fields.Integer(string='Phone', help="Phone number of the seller")
    mobile_number = fields.Integer(string='Mobile Number',
                                   help="Mobile number of the Seller shop")
    email = fields.Char(string='E-mail', help="Email address of the seller")
    fax = fields.Char(string='Fax', help="Fax of the seller")
    is_publish = fields.Boolean(string="Is Publish",
                                help="for identifying seller shop is published"
                                     "or not in the website")
    product_count = fields.Integer(string='Product Count',
                                   help="Total product count in the shop")
    product_ids = fields.Many2many('product.template',
                                   string="Product",
                                   help="Product details")
    state = fields.Selection(selection=[
        ('Pending for Approval', 'Pending for Approval'),
        ('Approved', 'Approved'), ('Denied', 'Denied')], string="State",
        help="State of the shop", default="Pending for Approval")

    def approve_request(self):
        """ Approve the seller shop request"""
        self.state = 'Approved'

    def reject_request(self):
        """ Reject the seller request"""
        self.state = 'Denied'

    def action_toggle_is_published(self):
        """ Toggle the field `is_published`."""
        if self.state == 'Approved':
            self.is_publish = not self.is_publish
        else:
            raise UserError(_("You can only publish the approved shops"))
