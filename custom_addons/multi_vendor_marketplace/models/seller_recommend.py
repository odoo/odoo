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


class SellerRecommend(models.Model):
    """Managing Seller Recommendations"""
    _name = 'seller.recommend'
    _description = 'Seller Recommendation'
    _rec_name = 'partner_id'
    _inherit = 'mail.thread'

    partner_id = fields.Many2one('res.partner', string="Customer",
                                 help="For getting customer name",
                                 required=True)
    seller_id = fields.Many2one('res.partner', string="Seller",
                                help="For getting seller name", required=True)
    recommend = fields.Selection(selection=[('no', 'NO'), ('yes', 'YES')],
                                 default='NO', track_visibility='always')
    date = fields.Date(string="Date", help="Storing date",
                       default=fields.Date.today, required=True)
    state = fields.Selection(selection=[('unpublished', 'Unpublished'),
                                        ('published', 'Published')],
                             string='Status',
                             help="Status of the Recommendation",
                             default='unpublished', track_visibility='always')

    @api.model
    def recommend_func(self, vals):
        """Create or update the recommendation for the seller by customers"""
        check = self.search([('seller_id', '=', int(vals['seller_id'])),
                             ('customer_id', '=', int(vals['customer_id']))])
        if check:
            check.write({'recommend': vals['recommend']})
        else:
            return super(SellerRecommend, self).create(vals)

    def action_publish(self):
        """ Function to change the state when publish the seller
                        recommendation"""
        self.write({'state': "published"})

    def action_unpublish(self):
        """ Function to change the state when the seller recommendation
                got unpublished """
        self.write({'state': "unpublished"})
