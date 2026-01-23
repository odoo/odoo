# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64

from collections import defaultdict

from odoo import _, api, fields, models, Command
from odoo.exceptions import ValidationError
from odoo.tools.image import is_image_size_above

from odoo.addons.html_editor.tools import get_video_embed_code, get_video_thumbnail


class ProductImage(models.Model):
    _name = 'product.image'
    _description = "Product Image"
    _inherit = ['image.mixin']
    _order = 'sequence, id'

    name = fields.Char(string="Name", required=True)
    sequence = fields.Integer(default=10)

    image_1920 = fields.Image()

    product_tmpl_id = fields.Many2one(
        string="Product Template", comodel_name='product.template', ondelete='cascade', index=True,
    )
    product_variant_ids = fields.Many2many(
        'product.product',
        string="Product Variants",
        relation='product_image_product_variant_rel',
        column1='product_image_id',
        column2='product_variant_id',
    )
    video_url = fields.Char(
        string="Video URL",
        help="URL of a video for showcasing your product.",
    )
    embed_code = fields.Html(compute='_compute_embed_code', sanitize=False)

    can_image_1024_be_zoomed = fields.Boolean(
        string="Can Image 1024 be zoomed",
        compute='_compute_can_image_1024_be_zoomed',
        store=True,
    )
    attribute_value_ids = fields.Many2many(
        'product.attribute.value',
    )
    is_template_image = fields.Boolean(
        compute='_compute_is_template_image',
        store=True,
        index=True,
    )

    #=== COMPUTE METHODS ===#

    @api.depends('image_1920', 'image_1024')
    def _compute_can_image_1024_be_zoomed(self):
        for image in self:
            image.can_image_1024_be_zoomed = image.image_1920 and is_image_size_above(image.image_1920, image.image_1024)

    @api.depends('video_url')
    def _compute_embed_code(self):
        for image in self:
            image.embed_code = image.video_url and get_video_embed_code(image.video_url) or False

    @api.depends('product_tmpl_id', 'product_variant_ids')
    def _compute_is_template_image(self):
        for image in self:
            image.is_template_image = bool(image.product_tmpl_id and not image.product_variant_ids)

    #=== ONCHANGE METHODS ===#

    @api.onchange('video_url')
    def _onchange_video_url(self):
        if not self.image_1920:
            thumbnail = get_video_thumbnail(self.video_url)
            self.image_1920 = thumbnail and base64.b64encode(thumbnail) or False

    #=== CONSTRAINT METHODS ===#

    @api.constrains('video_url')
    def _check_valid_video_url(self):
        for image in self:
            if image.video_url and not image.embed_code:
                raise ValidationError(_("Provided video URL for '%s' is not valid. Please enter a valid video URL.", image.name))

    #=== CRUD METHODS ===#

    @api.model_create_multi
    def create(self, vals_list):
        """
            We don't want the default_product_tmpl_id from the context
            to be applied if we have a product_variant_ids set to avoid
            having the variant images to show also as template images.
            But we want it if we don't have a product_variant_ids set.
        """
        context_without_template = self.with_context({k: v for k, v in self.env.context.items() if k != 'default_product_tmpl_id'})
        normal_vals = []
        variant_vals_list = []

        for vals in vals_list:
            if vals.get('product_variant_ids') and 'default_product_tmpl_id' in self.env.context:
                variant = self.env['product.product'].browse(vals['product_variant_ids'][0][1])
                vals['attribute_value_ids'] = [
                    (4, ptav.product_attribute_value_id.id) for ptav in variant.product_template_attribute_value_ids
                ]
                variant_vals_list.append(vals)
            else:
                normal_vals.append(vals)

        return super().create(normal_vals) + super(ProductImage, context_without_template).create(variant_vals_list)

    def write(self, vals):
        res = super().write(vals)
        if 'attribute_value_ids' in vals:
            self._sync_variant_images()
        return res

    # === BUSINESS METHODS === #

    def get_attribute_values_for_image_assignment(self):
        product_template = self.product_variant_ids[:1].product_tmpl_id or self.product_tmpl_id
        if not product_template:
            return []

        return [
            {
                'id': line.attribute_id.id,
                'name': line.attribute_id.name,
                'values': [
                    {
                        'id': ptav.product_attribute_value_id.id,
                        'name': ptav.product_attribute_value_id.name,
                    }
                    for ptav in line.product_template_value_ids
                    if ptav.ptav_active
                ],
            }
            for line in product_template.attribute_line_ids
        ]

    def _sync_variant_images(self):
        for image in self:
            product_template = image.product_variant_ids[:1].product_tmpl_id or image.product_tmpl_id

            if not product_template or not image.attribute_value_ids:
                image.product_variant_ids = [Command.clear()]
                continue

            image_vals_by_attr = defaultdict(set)
            for val in image.attribute_value_ids:
                image_vals_by_attr[val.attribute_id.id].add(val.id)

            compatible_variant_ids = []

            for variant in product_template.product_variant_ids:
                variant_vals = {
                    ptav.attribute_id.id: ptav.product_attribute_value_id.id
                    for ptav in variant.product_template_attribute_value_ids
                }

                if all(
                    variant_vals.get(attr_id) in allowed_vals
                    for attr_id, allowed_vals in image_vals_by_attr.items()
                ):
                    compatible_variant_ids.append(variant.id)

            image.product_variant_ids = [Command.set(compatible_variant_ids)]
