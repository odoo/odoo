# Part of Odoo. See LICENSE file for full copyright and licensing details.
import json
import re

from odoo import models, fields, api, Command, _

from odoo.addons.sale_gelato_connector.utils import make_gelato_request
from odoo.exceptions import ValidationError


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    gelato_reference = fields.Char(
        string="Gelato Reference",
        compute='_compute_gelato_reference',
        inverse='_set_gelato_reference',
    )
    gelato_template_ref = fields.Char(string="Gelato TemplateID")

    gelato_template_image = fields.Image()

    @api.constrains('gelato_reference', 'gelato_template_ref', 'gelato_template_image')
    def _check_gelato_image(self):
        for record in self:
            if record.gelato_template_ref or record.gelato_reference:
                if not record.gelato_template_image:
                    raise ValidationError(_("You must provide image template design for Gelato "
                                            "product."))

    @api.depends('product_variant_ids.gelato_reference')
    def _compute_gelato_reference(self):
        self._compute_template_field_from_variant_field('gelato_reference')

    def _set_gelato_reference(self):
        self._set_product_variant_field('gelato_reference')

    def _get_related_fields_variant_template(self):
        related_variants = super()._get_related_fields_variant_template()
        related_variants.append('gelato_reference')
        return related_variants

    def action_create_product_variants_from_gelato_template(self):
        """
            Make a request to Gelato to pass all the variants of provided template and create
            attributes corresponding to the variants, which will automatically create variants.
        """

        url = f'https://ecommerce.gelatoapis.com/v1/templates/{self.gelato_template_ref}'

        request = make_gelato_request(self.env.company, url=url, method='GET')
        data = json.loads(request.text)

        self.description_sale = re.sub('<[^<]+?>', '', data['description'])

        if len(data['variants']) == 1:
            self.gelato_reference = data['variants'][0]['productUid']

        else:
            for variant in data['variants']:
                variant_options_values_ids = []
                for attribute in variant['variantOptions']:

                    attribute_odoo = self.env['product.attribute'].search(
                        [('name', '=', attribute['name'])],
                        limit=1
                    )
                    if not attribute_odoo:
                        attribute_odoo = self.env['product.attribute'].create(
                            {'name': attribute['name']}
                        )

                    attribute_value = self.env['product.attribute.value'].search(
                        [
                            ('name', '=', attribute['value']),
                            ('attribute_id', '=', attribute_odoo.id)
                        ],
                        limit=1
                    )

                    if not attribute_value:
                        attribute_value = self.env['product.attribute.value'].create({
                            'name': attribute['value'],
                            'attribute_id': attribute_odoo.id
                        })
                    variant_options_values_ids.append(attribute_value.id)

                    product_template_attribute_line = self.env['product.template.attribute.line'].search([('product_tmpl_id', '=', self.id), ('attribute_id', '=', attribute_odoo.id)], limit=1)

                    if not product_template_attribute_line:
                        self.env['product.template.attribute.line'].create({
                            'product_tmpl_id': self.id,
                            'attribute_id': attribute_odoo.id,
                            'value_ids': [Command.link(attribute_value.id)]
                        })
                    else:
                        product_template_attribute_line.value_ids = [Command.link(attribute_value.id)]

                current_product = self.env['product.product'].search(
                    [('product_tmpl_id', '=', self.id)]
                )
                current_product = current_product.filtered(lambda s: set(s.product_template_attribute_value_ids.product_attribute_value_id.ids) == set(variant_options_values_ids))

                gelato_ref = variant['productUid']
                current_product[0].gelato_reference = gelato_ref

            variants_without_gelato = self.env['product.product'].search([
                ('product_tmpl_id', '=', self.id),
                ('gelato_reference', '=', False)
            ])
            variants_without_gelato.unlink()
