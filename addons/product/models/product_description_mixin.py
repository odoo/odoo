# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class ProductDescriptionMixin(models.AbstractModel):
    _name = 'product.description.mixin'
    _description = 'Product description Mixin'

    # This mixin uses a One2many field "product_custom_attribute_value_ids" which cannot be centralized in here
    # as this class will not be instancied and thus, as the relation between a table and a non-existing one
    # cannot exist, we need to add the field to all model that will use this mixin.

    product_id = fields.Many2one('product.product', 'Product')
    # M2M holding the values of product.attribute with create_variant field set to 'no_variant'
    # It allows keeping track of the extra_price associated to those attribute values and add them to the SO line description
    product_no_variant_attribute_value_ids = fields.Many2many(
        comodel_name='product.template.attribute.value',
        string="Extra Values",
        compute='_compute_no_variant_attribute_values',
        store=True, readonly=False, precompute=True, ondelete='restrict')
    is_configurable_product = fields.Boolean(
        string="Is the product configurable?",
        related='product_id.product_tmpl_id.has_configurable_attributes',
        depends=['product_id'])
    product_template_attribute_value_ids = fields.Many2many(
        related='product_id.product_template_attribute_value_ids',
        depends=['product_id'])
    product_description = fields.Text(
        string="Product Description",
        compute='_compute_product_description',
        store=True, readonly=False, precompute=True)

    @api.depends('product_id')
    def _compute_no_variant_attribute_values(self):
        for record in self:
            if not record.product_id:
                record.product_no_variant_attribute_value_ids = False
                continue
            if not record.product_no_variant_attribute_value_ids:
                continue
            valid_values = record.product_id.product_tmpl_id.valid_product_template_attribute_line_ids.product_template_value_ids
            # remove the no_variant attributes that don't belong to this template
            for ptav in record.product_no_variant_attribute_value_ids:
                if ptav._origin not in valid_values:
                    record.product_no_variant_attribute_value_ids -= ptav

    @api.depends('product_id')
    def _compute_product_description(self):
        for record in self:
            if not record.product_id:
                continue
            record.product_description = record._get_multiline_description()

    @api.depends('product_id')
    def _compute_custom_attribute_values(self):
        for record in self:
            if not record.product_id:
                record.product_custom_attribute_value_ids = False
                continue
            if not record.product_custom_attribute_value_ids:
                continue
            valid_values = record.product_id.product_tmpl_id.valid_product_template_attribute_line_ids.product_template_value_ids
            # remove the is_custom values that don't belong to this template
            for pacv in record.product_custom_attribute_value_ids:
                if pacv.custom_product_template_attribute_value_id not in valid_values:
                    record.product_custom_attribute_value_ids -= pacv

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('product_custom_attribute_value_ids'):
                continue
            for pcav in vals['product_custom_attribute_value_ids']:
                if not self.is_linkable_to_model(pcav):
                    continue
                pcav[2]['res_model'] = self._name
        return super().create(vals_list)

    def _get_multiline_description(self):
        """ Compute a default multiline description.
        In most cases the product description is enough.
        e.g:
        - custom attributes and attributes that don't create variants, both introduced by the "product configurator"
        """
        self.ensure_one()
        return self.product_id.display_name + self._get_multiline_description_variants()

    def _get_multiline_description_variants(self):
        """When using no_variant attributes or is_custom values, the product
        itself is not sufficient to create the description: we need to add
        information about those special attributes and values.
        :return: the description related to special variant attributes/values
        :rtype: string
        """
        if not self.product_custom_attribute_value_ids and not self.product_no_variant_attribute_value_ids:
            return ""

        name = ""

        custom_ptavs = self.product_custom_attribute_value_ids.custom_product_template_attribute_value_id
        no_variant_ptavs = self.product_no_variant_attribute_value_ids._origin

        # display the no_variant attributes, except those that are also
        # displayed by a custom (avoid duplicate description)
        for ptav in (no_variant_ptavs - custom_ptavs):
            name += "\n" + ptav.display_name

        # Sort the values according to _order settings, because it doesn't work for virtual records in onchange
        sorted_custom_ptav = self.product_custom_attribute_value_ids.custom_product_template_attribute_value_id.sorted()
        for patv in sorted_custom_ptav:
            pacv = self.product_custom_attribute_value_ids.filtered(lambda pcav: pcav.custom_product_template_attribute_value_id == patv)
            name += "\n" + pacv.display_name
        return name

    def is_linkable_to_model(self, pcav):
        if len(pcav[2]) == 0:
            return False
        return True
