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


class SellerReview(models.Model):
    """Managing Seller Reviews"""
    _name = 'seller.review'
    _description = 'Seller Review'
    _rec_name = 'review_title'
    _inherit = 'mail.thread'

    seller_id = fields.Many2one('res.partner', string="Seller",
                                help="Getting seller name",
                                required=True)
    customer_id = fields.Many2one('res.partner', required=True,
                                  string="Customer",
                                  help="Getting partner name")
    customer_email = fields.Char(related='customer_id.email',
                                 string="Email", help="Getting customer email")
    rating = fields.Float(string="Rating", help="Getting rating",
                          required=True)
    review_title = fields.Char(string="Review Title",
                               help="Title of the review")
    date = fields.Date(string="Date", help="Date field",
                       default=fields.Date.today)
    message = fields.Text(string="Message",
                          help="Field to enter the review text", size=150)
    like_count = fields.Integer(string='Helpful Count',
                                help="Count of the positive review",
                                compute='_compute_count')
    unlike_count = fields.Integer('Found Not Helpful',
                                  help="Count of all negative reviews",
                                  compute='_compute_count')
    state = fields.Selection(selection=[('unpublished', 'Unpublished'),
                                        ('published', 'Published')],
                             string='Status', help="state of the review",
                             default='unpublished', track_visibility='always')
    help_info_ids = fields.One2many('helpful.info', 'review_id',
                                    string="Help info",
                                    help="Helpful info details")
    _sql_constraints = [
        ('rating_range', 'check(rating >= 0 and rating <= 5)',
         'Rating should be between 0 and 5')]

    @api.model
    def rate_review(self, vals):
        """For adding Seller review"""
        check = self.sudo().search([('seller_id', '=', int(vals['seller_id'])),
                                    ('customer_id', '=',
                                     int(vals['customer_id']))])
        publish = self.env['ir.config_parameter'].sudo().get_param(
            'multi_vendor_marketplace.auto_publish_seller_review')
        if check:
            if publish:
                check.sudo().write({'rating': vals['rating'],
                                    'message': vals['message']})
                check.pub()
            else:
                check.write({'rating': vals['rating'],
                             'message': vals['message']})
                check.unpub()
        else:
            if publish:
                check.sudo().pub()
                return super(SellerReview, self).sudo().create(vals)
            else:
                check.sudo().unpub()
                return super(SellerReview, self).sudo().create(vals)

    def action_publish(self):
        """ Function to publish the review"""
        self.state = 'published'

    def action_unpublish(self):
        """ Function to un publish the review"""
        self.state = 'unpublished'

    def _compute_count(self):
        """ Function to compute the total count """
        count = None
        for record in self:
            count = record.env['helpful.info'].search_count(
                [('review_id', '=', record.id)])
        if count:
            for record in self:
                for rec in record.help_info_ids:
                    record.like_count = rec.search_count([('msg', '=', 'yes'),
                                                          ('review_id', '=',
                                                           record.id)])
                    record.unlike_count = rec.search_count([('msg', '=', 'no'),
                                                            ('review_id', '=',
                                                             record.id)])
        else:
            for record in self:
                record.like_count = record.unlike_count = 0
