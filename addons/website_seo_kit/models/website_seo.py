# -*- coding: utf-8 -*-
################################################################################
#
#    Cybrosys Technologies Pvt. Ltd.
#
#    Copyright (C) 2023-TODAY Cybrosys Technologies(<https://www.cybrosys.com>).
#    Author: Cybrosys Techno Solutions (odoo@cybrosys.com)
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
############################################################################
from odoo import api, exceptions, fields, models


class WebsiteSeoAttribute(models.Model):
    """This module allows to user to give attributes"""
    _name = 'website.seo.attributes'
    _description = 'Website SEO'

    name = fields.Char(string='Name', required=True, help='Name')
    product = fields.Selection([('name', 'Product Name'),
                                ('description', 'Description for Quotations'),
                                ('description_sale', 'Product Description'),
                                ('default_code', 'Internal Reference'),
                                ('company_id', 'Company Name')],
                               help='Select Product', string="Product")
    models = fields.Selection([('product', 'Product'),
                               ('product_category', 'Product Category')],
                              string='Model', help='Choose your model')
    tech_name = fields.Char(string='Technical name', help="Technical Name")
    category = fields.Selection([('name', 'Category Name'),
                                 ('parent_id', 'Category Parent Name'),
                                 ('category_description',
                                  'Category Description')],
                                help='Select Product Category',
                                string="Select Product Category")

    @api.constrains('name')
    def _check_unique_name(self):
        """Check for unique name"""
        for rec in self:
            domain = [('name', '=', rec.name.lower())]
            if self.search_count(domain) > 1:
                raise exceptions.ValidationError("Name must be unique.")


class GenerateSeo(models.Model):
    """In this model user can generate seo
    based on product or product category"""
    _name = 'seo.generate'
    _description = 'Generate SEO'
    _rec_name = 'model_name'

    model_name = fields.Selection([('product', 'Product'),
                                   ('product_category', 'Product Category')],
                                  string='SEO Meta Configuration For',
                                  help='Select any these model', required=True)
    meta_title_ids = fields.Many2many('website.seo.attributes',
                                      'title', 'title_id', string='Meta Title',
                                      help='Choose meta tittle', required=True)
    meta_description_ids = fields.Many2many('website.seo.attributes',
                                            'description', 'description_id',
                                            string='Meta Description',
                                            help='Choose meta description',
                                            required=True)
    attribute_separator = fields.Char(string="Multi Attribute Separator",
                                      default="|", required=True)
    company_id = fields.Many2one('res.company', string='Company',
                                 default=lambda self: self.env.company)
    meta_ids = fields.Many2many('website.seo.attributes', 'meta', 'meta_id',
                                string='Title !')
    state = fields.Selection([
        ('activated', 'Activated'), ('deactivated', 'Deactivated')],
        string='Status', default='deactivated')

    @api.onchange('model_name')
    def _onchange_model_name(self):
        self.meta_title_ids = False
        self.meta_description_ids = False
        model_name = self.model_name
        if model_name == 'product':
            self.meta_ids = [rec.id for rec in
                             self.env['website.seo.attributes'].search(
                                 [('models', '=', 'product')])]
        elif model_name == 'product_category':
            self.meta_ids = [rec.id for rec in
                             self.env['website.seo.attributes'].search(
                                 [('models', '=', 'product_category')])]

    def action_save_seo_info(self):
        """Save the seo content"""
        for rec in self.search([]):
            if rec.id == self.id:
                self.write({'state': 'activated'})
            else:
                rec.write({'state': 'deactivated'})
        if self.model_name == 'product':
            if self.meta_title_ids:
                products = self.env['product.template'].search_read(
                    [], fields=self.meta_title_ids.mapped('product'))
                meta_title = []
                for product in products:
                    sep = self.attribute_separator
                    string = str(sep).join(
                        str(product[x]) for x in product.keys() if x != 'id')
                    string = string.translate({
                        ord(i): None for i in "<p>(),'</p>"})
                    values = {
                        'string': string,
                        'id': product['id']
                    }
                    pro = self.env['product.template'].browse(values['id'])
                    pro.write({
                        'website_meta_title': values['string'],
                        'website_meta_keywords': pro.name
                    })
                    meta_title.append(values)
            if self.meta_description_ids:
                products = self.env['product.template'].search_read(
                    [], fields=self.meta_description_ids.mapped('product'))
                meta_description = []
                for product in products:
                    sep = self.attribute_separator
                    string = str(sep).join(
                        str(product[x]) for x in product.keys() if x != 'id')
                    string = string.translate(
                        {ord(i): None for i in "<p>(),'</p>"})
                    values = {
                        'string': string,
                        'id': product['id']
                    }
                    pro = self.env['product.template'].browse(values['id'])
                    pro.write({
                        'website_meta_description': values['string'],
                    })
                    meta_description.append(values)
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'target': 'new',
                'params': {
                    'message': ("Successfully "
                                "generated the seo for all products"),
                    'type': 'success',
                    'sticky': False,
                }
            }
        elif self.model_name == 'product_category':
            if self.meta_title_ids:
                products = self.env['product.public.category'].search_read(
                    [('is_auto_seo', '=', True)],
                    fields=self.meta_title_ids.mapped('category'))
                meta_categ_title = []
                for product in products:
                    sep = self.attribute_separator
                    string = str(sep).join(
                        str(product[x]) for x in product.keys() if x != 'id')
                    string = string.translate(
                        {ord(i): None for i in "<p>(),'</p>"})
                    values = {
                        'string': string,
                        'id': product['id']
                    }
                    pro = self.env['product.public.category'].browse(
                        values['id'])
                    for rec in pro:
                        rec.write({
                            'website_meta_title': values['string'],
                            'website_meta_keywords': pro.name
                        })
                    meta_categ_title.append(values)
            if self.meta_description_ids:
                products = self.env['product.public.category'].search_read(
                    [('is_auto_seo', '=', True)],
                    fields=self.meta_description_ids.mapped('category'))
                meta_categ_description = []
                for product in products:
                    sep = self.attribute_separator
                    string = str(sep).join(
                        str(product[x]) for x in product.keys() if x != 'id')
                    string = string.translate(
                        {ord(i): None for i in "<p>(),'</p>"})
                    values = {
                        'string': string,
                        'id': product['id']
                    }
                    pro = self.env[
                        'product.public.category'].browse(values['id'])
                    pro.write({
                        'website_meta_description': values['string'],
                    })
                    meta_categ_description.append(values)
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'target': 'new',
                'params': {
                    'message':
                        ("Successfully created the SEO only for product"
                         " groups with auto SEO enabled."),
                    'type': 'success',
                    'sticky': False,
                }
            }


class SeoPublicCategory(models.Model):
    """Here user can include category by enabling is_auto_seo field"""
    _inherit = 'product.public.category'

    is_auto_seo = fields.Boolean(string="Auto Update SEO",
                                 help='enable for generate seo content '
                                      'automatically for this category')
    category_description = fields.Text(string='Description For This Category',
                                       help='Description For This Category')
