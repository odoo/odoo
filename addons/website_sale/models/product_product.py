# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class Product(models.Model):
    _inherit = "product.product"

    website_id = fields.Many2one(related='product_tmpl_id.website_id', readonly=False)

    product_variant_image_ids = fields.One2many('product.image', 'product_variant_id', string="Extra Variant Images")

    website_url = fields.Char('Website URL', compute='_compute_product_website_url', help='The full URL to access the document through the website.')

    base_unit_count = fields.Float('Base Unit Count', required=True, default=1, help="Display base unit price on your eCommerce pages. Set to 0 to hide it for this product.")
    base_unit_id = fields.Many2one('website.base.unit', string='Custom Unit of Measure', help="Define a custom unit to display in the price per unit of measure field.")
    base_unit_price = fields.Monetary("Price Per Unit", currency_field="currency_id", compute="_compute_base_unit_price")
    base_unit_name = fields.Char(compute='_compute_base_unit_name', help='Displays the custom unit for the products if defined or the selected unit of measure otherwise.')

    @api.depends('price', 'lst_price', 'base_unit_count')
    def _compute_base_unit_price(self):
        for product in self:
            if not product.id:
                product.base_unit_price = 0
            else:
                product.base_unit_price = product.base_unit_count and (product.price or product.lst_price) / product.base_unit_count

    @api.depends('uom_name', 'base_unit_id')
    def _compute_base_unit_name(self):
        for product in self:
            product.base_unit_name = product.base_unit_id.name or product.uom_name

    @api.constrains('base_unit_count')
    def _check_base_unit_count(self):
        if any(product.base_unit_count < 0 for product in self):
            raise ValidationError(_('The value of Base Unit Count must be greater than 0. Use 0 to hide the price per unit on this product.'))

    @api.depends_context('lang')
    @api.depends('product_tmpl_id.website_url', 'product_template_attribute_value_ids')
    def _compute_product_website_url(self):
        for product in self:
            attributes = ','.join(str(x) for x in product.product_template_attribute_value_ids.ids)
            product.website_url = "%s#attr=%s" % (product.product_tmpl_id.website_url, attributes)

    def _prepare_variant_values(self, combination):
        variant_dict = super()._prepare_variant_values(combination)
        variant_dict['base_unit_count'] = self.base_unit_count
        return variant_dict

    def website_publish_button(self):
        self.ensure_one()
        return self.product_tmpl_id.website_publish_button()

    def open_website_url(self):
        self.ensure_one()
        res = self.product_tmpl_id.open_website_url()
        res['url'] = self.website_url
        return res

    def _get_images(self):
        """Return a list of records implementing `image.mixin` to
        display on the carousel on the website for this variant.

        This returns a list and not a recordset because the records might be
        from different models (template, variant and image).

        It contains in this order: the main image of the variant (if set), the
        Variant Extra Images, and the Template Extra Images.
        """
        self.ensure_one()
        variant_images = list(self.product_variant_image_ids)
        if self.image_variant_1920:
            # if the main variant image is set, display it first
            variant_images = [self] + variant_images
        else:
            # If the main variant image is empty, it will fallback to template
            # image, in this case insert it after the other variant images, so
            # that all variant images are first and all template images last.
            variant_images = variant_images + [self]
        # [1:] to remove the main image from the template, we only display
        # the template extra images here
        return variant_images + self.product_tmpl_id._get_images()[1:]

    def _is_sold_out(self):
        combination_info = self.with_context(website_sale_stock_get_quantity=True).product_tmpl_id._get_combination_info(product_id=self.id)
        return combination_info['product_type'] == 'product' and combination_info['free_qty'] <= 0
