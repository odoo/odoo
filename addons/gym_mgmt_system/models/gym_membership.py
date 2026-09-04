# -*- coding: utf-8 -*-
#############################################################################
#
#    Cybrosys Technologies Pvt. Ltd.
#
#    Copyright (C) 2023-TODAY Cybrosys Technologies(<https://www.cybrosys.com>)
#    Author: Sahla Sherin (<https://www.cybrosys.com>)
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
from odoo import api, fields, models, _


class GymMembership(models.Model):
    """This model is for gym membership."""
    _name = "gym.membership"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _description = "Gym Membership"
    _rec_name = "reference"

    reference = fields.Char(string='GYM reference',readonly=True,
                            default=lambda self: _('New'))
    member_id = fields.Many2one('res.partner', string='Member',
                                required=True, tracking=True,
                                domain="[('gym_member', '!=',False)]")
    membership_scheme_id = fields.Many2one('product.product',
                                           string='Membership scheme',
                                           required=True, tracking=True,
                                           domain="[('membership_date_from', "
                                                  "'!=',False)]")
    paid_amount = fields.Float(string="Paid Amount", tracking=True)
    membership_fees = fields.Float(string="Membership Fees", tracking=True,
                                   related="membership_scheme_id.list_price")
    sale_order_id = fields.Many2one('sale.order', string='Sales Order',
                                    ondelete='cascade', copy=False,
                                    readonly=True)
    membership_date_from = fields.Date(string='Membership Start Date',
                                       related="membership_scheme_id."
                                               "membership_date_from",
                                       help='Date from which membership '
                                            'becomes active.')
    membership_date_to = fields.Date(string='Membership End Date',
                                     related="membership_scheme_id.membership_"
                                             "date_to",
                                     help='Date until which membership remains'
                                          'active.')
    company_id = fields.Many2one('res.company', string='Company',
                                 default=lambda self: self.env.company,
                                 help='The field hold the company id')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirm', 'Confirm'),
        ('cancelled', 'Cancelled')
    ], default='draft', string='Status',
        help="The status of record defined here")

    _sql_constraints = [
        ('membership_date_greater',
         'check(membership_date_to >= membership_date_from)',
         'Error ! Ending Date cannot be set before Beginning Date.')
    ]

    @api.model
    def create_multi(self, vals):
        """Sequence number for membership """
        if vals.get('reference', ('New')) == ('New'):
            vals['reference'] = self.env['ir.sequence'].next_by_code(
                'gym.membership') or ('New')
        res = super(GymMembership, self).create(vals)
        return res
