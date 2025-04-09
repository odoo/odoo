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


class ProductTemplate(models.Model):
    """Inheriting ProductTemplate For adding new fields and Functions"""
    _inherit = "product.template"

    website_category_id = fields.Many2one('product.public.category',
                                          string='Website category',
                                          help='Website category')
    cmpy_email = fields.Text(
        default=lambda self: self.env.user.company_id.email,
        string='Company email',
        help='Company address')
    seller_id = fields.Many2one(
        'res.partner', string='Seller',
        help='Seller',
        default=lambda self: self.env.user.partner_id.id,
        domain=[('state', '=', 'Approved')])
    seller_pic = fields.Binary(related='seller_id.image_1920',
                               string='Seller image', help='Seller image')
    web = fields.Many2one("website", string="Website",
                          help='Website')
    alt_pro_id = fields.Many2one("product.template",
                              string="Alternative Products",
                              help='Alternative Products')
    acc_pro_id = fields.Many2one("product.template",
                              string="Accessory Products",
                              help='Accessory products')
    forcasted_qty = fields.Integer(string='Forcasted quantity',
                                   help='Forcasted quantity')
    initial_qty = fields.Integer(string='Initial quantity',
                                 help='Initial quantity')
    state = fields.Selection(
        [('draft', 'Draft'), ('pending', 'pending'),
         ('approved', 'Approved'), ('rejected', 'Rejected')],
        string='Product Status', group_expand='_group_expand_states',
        default='draft', help='Product Status', track_visibility='always',
        readonly=True)
    item_ids = fields.One2many('multi.vendor.pricelist',
                               'product_inv_id', string='Items',
                               help='Items')
    product_price_setting = fields.Boolean(string='Product price setting',
                                           help='Product price setting')
    product_variants_setting = fields.Boolean(string='Product variants '
                                                     'settings',
                                              help='Product variants settings')
    product_uom = fields.Boolean(string='Product uom', help='Product uom')

    def _create(self, data_list):
        """Supering the create function to change category """
        res = super(ProductTemplate, self)._create(data_list)
        self.categ_id = [self.env['ir.config_parameter'].sudo().get_param(
            'multi_vendor_marketplace.internal_categ_id')]
        return res

    def write(self, vals):
        """ Pricelist Creation from Product form view """
        res = super(ProductTemplate, self).write(vals)
        for wdata in self.item_ids:
            data_module = self.env['product.pricelist.item'].search(
                [('pricelist_id', '=', wdata.price_list_id.id)])
            if data_module:
                dictionary = {}
                dictionary.clear()
                for data in data_module:
                    dictionary[data.pricelist_multivendor_id.id] = data
                if wdata._origin.id in dictionary.keys():
                    dictionary[wdata._origin.id].update({
                        'product_tmpl_id': self._origin.id,
                        'min_quantity': wdata.min_qty,
                        'fixed_price': wdata.price_of_pricelist,
                        'date_start': wdata.start_date,
                        'date_end': wdata.end_date,
                    })
                else:
                    wdata.price_list_id.write({'item_ids': [(0, 0, {
                        'product_tmpl_id': self._origin.id,
                        'min_quantity': wdata.min_qty,
                        'fixed_price': wdata.price_of_pricelist,
                        'date_start': wdata.start_date,
                        'date_end': wdata.end_date,
                        'pricelist_multivendor_id': wdata._origin.id
                    })]})
            else:
                wdata.price_list_id.write({'item_ids': [(0, 0, {
                    'product_tmpl_id': self._origin.id,
                    'min_quantity': wdata.min_qty,
                    'fixed_price': wdata.price_of_pricelist,
                    'date_start': wdata.start_date,
                    'date_end': wdata.end_date,
                    'pricelist_multivendor_id': wdata._origin.id
                })]})
        return res

    def send_product_status_mail(self):
        """For sending product status mail"""
        params = self.env[
            'res.config.settings'].search([],
                                          order='create_date desc', limit=1)
        product_approve_admin_mail = params.product_approve_admin_mail
        product_approve_seller_mail = params.product_approve_seller_mail
        if product_approve_admin_mail:
            name = params.product_approve_admin_mail_template_id.name
            template = self.env['mail.template'].sudo().search(
                [('name', '=', name)], limit=1)
            self.env['mail.template'].browse(template.id).send_mail(
                self.id, force_send=True)
        if product_approve_seller_mail:
            name = params.product_approve_seller_mail_template_id.name
            template = self.env['mail.template'].sudo().search(
                [('name', '=', name)], limit=1)
            self.env['mail.template'].browse(
                template.id).send_mail(self.id, force_send=True)

    def change_state_approved(self):
        """ Change product state to Approved when Admin approved """
        self.state = 'approved'
        self.send_product_status_mail()
        self.product_price_setting = self.env[
            'ir.config_parameter'].sudo().get_param(
            'multi_vendor_marketplace.product_pricing')
        self.product_variants_setting = self.env[
            'ir.config_parameter'].sudo().get_param(
            'multi_vendor_marketplace.product_variants')
        self.product_uom = self.env[
            'ir.config_parameter'].sudo().get_param(
            'multi_vendor_marketplace.uom')

    @api.onchange('name')
    def _onchange_name(self):
        """Automatically updates the product's internal category when the
        product name is changed."""
        internal_category = self.env['ir.config_parameter'].sudo().get_param(
            'multi_vendor_marketplace.internal_categ_id')
        self.categ_id = self.env['product.category'].browse(
            internal_category).id

    def change_state_pending(self):
        """ CHANGE PRODUCT TO PENDING STATE WHEN USER SEND REQUEST FOR
        PRODUCT """
        if self.env['ir.config_parameter'].sudo().get_param(
                'multi_vendor_marketplace.product_approval'):
            self.state = 'approved'
            self.sudo().send_product_status_mail()
        else:
            self.state = 'pending'
            self.sudo().send_product_status_mail()

    def change_state_reject(self):
        """ WHEN ADMIN REJECT THE PRODUCT REQUEST STATE CHANGE TO REJECTED """
        self.state = 'rejected'
        self.send_product_status_mail()

    def toggle_website_published(self):
        """ PUBLISH THE PRODUCT IN WEBSITE """
        self.is_published = not self.is_published


    def _group_expand_states(self):
        """Expands the selection options for the 'state' field in a group-by
         operation."""
        return [key for key, val in type(self).state.selection]
