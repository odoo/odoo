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


class ResPartner(models.Model):
    """ Inheriting partner to add sellers,marketplace and commission
         information etc"""
    _inherit = 'res.partner'

    profile_url = fields.Char(string='Profile Url', help="Url of the Profile")
    allow_product_variant = fields.Boolean(
        string='Allow Product Variant',
        help="True if access product variant")
    payment_method_ids = fields.Many2many('account.payment.method',
                                          string="Payment Methods",
                                          help="For accessing payment methods")
    total_amount = fields.Float(string='Total Amount',
                                help="Total amount by the seller")
    balance_amount = fields.Float(string='Balance Amount',
                                  hrlp="Amount balance for the seller")
    paid_amount = fields.Float(string='Paid Amount', help="Amount total paid")
    market_place_currency = fields.Monetary(string="Market Place Currency",
                                            help="Currency for the "
                                                 "marketplace ")
    currency_id = fields.Many2one("res.currency",
                                  string="Currency",
                                  help="Currency",
                                  default=lambda self: self.env
                                  ['res.currency'].search([
                                      ('name', '=', 'USD')]).id,
                                  readonly=True, hide=True)
    return_policy = fields.Html(string='Return Policies',
                                help="Product return policy for seller")
    shipping_policy = fields.Html(string='Shipping Policies',
                                  help="Product shipping policy can be set")
    profile_image = fields.Binary(string='Profile Image',
                                  help="Profile image in the website")
    profile_banner = fields.Binary(string='Profile Banner',
                                   help="Profile banner for the seller")
    profile_message = fields.Html(string="profile Message",
                                  help="Profile message for the seller")
    sale_count = fields.Integer(compute='_compute_sale_count',
                                sting="Sale Count",
                                help="For getting total sale count for seller")
    amount_available = fields.Float(compute='_compute_amount_available',
                                    string="Amount available")
    avg_rating = fields.Float(compute='_compute_avg_rating',
                              string="Average rating",
                              help="Average rating received by the seller")
    recommend_count = fields.Float(compute='_compute_recommend_count',
                                   string="Recommended count of the seller",
                                   help="Total recommended count of the seller")
    is_publish = fields.Boolean(string="Is publish", help="Check if it is "
                                                          "Published")
    publish = fields.Boolean(string="publish", help="Published")
    seller_shop_id = fields.Many2one('seller.shop',
                                     string="Seller shop",
                                     help="Seller shop details", domain="[('seller_id', '=', id)]")
    state = fields.Selection(
        selection=[('new', 'New'),
                   ('Pending for Approval', 'Pending for Approval'),
                   ('Approved', 'Approved'), ('Denied', 'Denied')],
        default="new",
        string='Seller Status', help="The status of the seller",
        group_expand='_group_expand_states',
        track_visibility='always')
    default_commission = fields.Float(string='Default Sale Commission(%)',
                                      help="For getting the default commission")
    amount_limit = fields.Float(
        string='Amount limit for seller payment request',
        help="Amount limit to be set for the seller payment request")
    min_gap = fields.Integer(string='Minimum gap for next payment request',
                             help="Minimum gap for the next payment request")
    auto_product_approve = fields.Boolean(string="Auto Product Approve",
                                          help="Automatically approve"
                                               "for product for sellers")
    auto_quality_approve = fields.Boolean()
    location_id = fields.Many2one('stock.location',
                                  string='Default Location',
                                  help="For getting stock location in "
                                       "warehouse")
    warehouse_id = fields.Many2one('stock.warehouse',
                                   string='Default Warehouse',
                                   help="For getting default warehouse")
    total_commission = fields.Float(string="Total commission",
                                    help="Total commission for the seller")
    commission = fields.Float(string="Commission",
                              help="For getting commission percentage")
    profile_url_value = fields.Char(string='Profile Url Value',
                                    help="profile url value")

    def req_approve(self):
        """ New user requested for approve to sell products """
        auto_approval = self.env['ir.config_parameter'].sudo().get_param(
            'multi_vendor_marketplace.seller_approval')
        if auto_approval:
            self.sudo().approve_seller()
            self.state = 'Approved'
        else:
            self.state = 'Pending for Approval'

    def user_my_profile(self):
        """ Fetch user profile """
        return {
            'type': 'ir.actions.act_window',
            'name': 'My Profile',
            'res_model': 'res.partner',
            'view_mode': 'form',
            'res_id': self.env['res.users'].broswe(
                self.env.user.id).partner_id.id,
            'target': 'new',
        }

    def new_user_my_profile(self):
        """ Fetch user profile """
        user_id = self.env['res.users'].search([('id', '=', self.env.user.id)])
        return {
            'type': 'ir.actions.act_window',
            'name': 'My Profile',
            'res_model': 'res.partner',
            'view_mode': 'form',
            'res_id': user_id.partner_id.id,
        }

    def publish(self):
        """ Publish user profile in website seller list """
        if not self.is_published:
            self.is_published = True
        else:
            self.is_published = False

    def view_settings(self):
        """ View default settings for sellers """
        commission_value = self.env['ir.config_parameter'].sudo().get_param(
            'multi_vendor_marketplace.commission')
        min_gap_value = self.env['ir.config_parameter'].sudo().get_param(
            'multi_vendor_marketplace.min_gap')
        amt_limit_value = self.env['ir.config_parameter'].sudo().get_param(
            'multi_vendor_marketplace.amt_limit')
        return {
            'name': 'Default Settings',
            'res_model': 'settings.view',
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'view_type': 'form',
            'target': 'new',
            'context': dict(
                self.env.context,
                default_commission=commission_value,
                default_amt_limit=amt_limit_value,
                default_minimum_gap=min_gap_value,
            ),
        }

    def approve(self):
        """ Seller approve state also changed """
        self.state = 'Approved'

    def _group_expand_states(self):
        """Returns a list of states"""
        return [key for key, val in type(self).state.selection]

    def register_payment(self):
        """ fast payment request form """
        return {
            'name': 'Payment Request',
            'domain': [],
            'res_model': 'request.payment',
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'view_type': 'form',
            'context': {},
            'target': 'new',
        }

    @api.model
    def create(self, vals):
        res = super(ResPartner, self).create(vals)
        params = self.env[
            'res.config.settings'].search([],
                                          order='create_date desc', limit=1)
        context = {'seller': vals['name'], }
        if params.seller_request_admin_mail:
            name = params.seller_request_admin_mail_template_id.name
            template = self.env['mail.template'].sudo().search(
                [('name', '=', name)], limit=1)
            self.env['mail.template'].browse(template.id).with_context(
                context).send_mail(self.id, force_send=True)
        if params.seller_request_seller_mail:
            name = params.seller_request_seller_mail_template_id.name
            template = self.env['mail.template'].sudo().search(
                [('name', '=', name)], limit=1)
            self.env['mail.template'].browse(template.id).with_context(
                context).send_mail(self.id,
                                   force_send=True)
        return res

    def send_seller_status_mail(self):
        """Send the seller status email"""
        params = self.env[
            'res.config.settings'].sudo().search([],
                                                 order='create_date desc',
                                                 limit=1)
        if params.sudo().seller_approve_admin_mail:
            name = params.sudo().seller_approve_admin_mail_template_id.name
            template = self.env['mail.template'].sudo().search(
                [('name', '=', name)], limit=1)
            self.env['mail.template'].sudo().browse(
                template.id).send_mail(self.id, force_send=True)
        if params.sudo().seller_approve_seller_mail:
            name = params.sudo().seller_approve_seller_mail_template_id.name
            template = self.env['mail.template'].sudo().search(
                [('name', '=', name)], limit=1)
            self.env['mail.template'].sudo().browse(
                template.id).send_mail(self.id, force_send=True)

    def approve_seller(self):
        """Approve the seller"""
        user1 = self.env["res.users"].search([("name", "=", self.name)])
        internal = self.env.ref('base.group_user')
        stock_group = self.env.ref('stock.group_stock_user')
        sale_group = self.env.ref('sales_team.group_sale_manager')
        seller_user = self.env.ref(
            "multi_vendor_marketplace.multi_vendor_marketplace_seller")
        user1.sudo().write({'groups_id': [(6, 0, [
            internal.id,
            seller_user.id,
            stock_group.id,
            sale_group.id
        ])]})
        result = self.env.ref('sales_team.group_sale_salesman')
        result1 = self.env.ref('sales_team.group_sale_salesman_all_leads')
        for user in result.users:
            if user in user1:
                result.write({'users': [(3, user.id, 0)]})
        for user in result1.users:
            if user in user1:
                result1.write({'users': [(3, user.id, 0)]})
        if self.state == 'Pending for Approval':
            self.state = 'Approved'
            self.send_seller_status_mail()

    def reject_seller(self):
        """Change the state to denied"""
        self.state = 'Denied'
        self.send_seller_status_mail()

    def create_shop(self):
        """Create a new shop"""
        return {
            'name': 'Seller Shop',
            'domain': [],
            'res_model': 'seller.shop',
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'view_type': 'form',
            'target': 'new',
        }

    def _group_expand_states(self):
        """ For expanding the values for selection field """
        return [key for
                key, val in type(self).state.selection]

    def _compute_sale_count(self):
        """ count seller sale count and display in the profile """
        for record in self:
            record.sale_count = self.env['sale.order.line'].search_count(
                [('seller_id', '=', self.id)])

    def _compute_amount_available(self):
        """ display available amount in seller profile """
        for avl_amt in self:
            avl_amt.amount_available = self.commission

    def view_sale_order(self):
        """ view sale order from seller profile """
        return {
            'type': 'ir.actions.act_window',
            'name': 'Orders',
            'view_mode': 'kanban,form',
            'res_model': 'sale.order.line',
            'domain': [('seller_id', '=', self.id)],
        }

    def _compute_avg_rating(self):
        """Compute the rating of seller"""
        for record in self:
            count = self.env['seller.review'].search_count(
                [('seller_id', '=', record.id)])
            if count:
                record.avg_rating = sum_rating = 0.0
                for rec in self.env['seller.review'].search([('seller_id', '=',
                                                              record.id)]):
                    sum_rating += rec.rating
                record.avg_rating += sum_rating / count
            else:
                record.avg_rating = 0

    def view_rating(self):
        """Return the seller review"""
        return {
            'type': 'ir.actions.act_window',
            'name': 'Rating in Review',
            'view_mode': 'tree,form',
            'res_model': 'seller.review',
            'domain': [('seller_id', '=', self.id)],
        }

    def _compute_recommend_count(self):
        """Compute recommendations"""
        for record in self:
            record.recommend_count = self.env['seller.recommend'].search_count(
                [('seller_id', '=', record.id), ('recommend', '=', 'yes')])

    def view_recommend(self):
        """Return the number of recommendations"""
        return {
            'type': 'ir.actions.act_window',
            'name': 'Recommendations',
            'view_mode': 'kanban',
            'res_model': 'seller.recommend',
            'domain': [('seller_id', '=', self.id), ('recommend', '=', 'yes')],
        }
