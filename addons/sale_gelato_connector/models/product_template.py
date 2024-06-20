# Part of Odoo. See LICENSE file for full copyright and licensing details.
import json
import requests

from odoo import models, fields, api, Command


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    gelato_reference = fields.Char(string="Gelato Reference", compute='_compute_gelato_reference', inverse='_set_gelato_reference')
    gelato_template_id = fields.Char(string="Gelato TemplateID")
    gelato_photo_url = fields.Char(string="Gelato Image", required=True)

    @api.depends('product_variant_ids.gelato_reference')
    def _compute_gelato_reference(self):
        self._compute_template_field_from_variant_field('gelato_reference')

    def _set_gelato_reference(self):
        self._set_product_variant_field('gelato_reference')

    def _get_related_fields_variant_template(self):
        related_variants = super()._get_related_fields_variant_template()
        related_variants.append('gelato_reference')
        return related_variants

    def create_product_variants_from_gelato_template(self):

        api_key = self.env.company.gelato_api_key

        headers = {
            'Content-Type': 'application/json',
            'X-API-KEY': api_key
        }

        url = 'https://ecommerce.gelatoapis.com/v1/templates/' + self.gelato_template_id

        request = requests.request("GET", url=url, headers=headers)
        data = json.loads(request.text)

        self.description_sale = data['description']
        self.name = data['title']

        if len(data['variants']) == 1:
            self.gelato_reference = data['variants'][0]['productUid']

        else: #maybe throw it in seprate function "create_variants_from_template"
            for variant in data['variants']:
                variant_options_values_ids = []
                for attribute in variant['variantOptions']:

                    attribute_odoo = self.env['product.attribute'].search([('name', '=', attribute['name'])], limit=1)
                    if not attribute_odoo:
                        attribute_odoo = self.env['product.attribute'].create({'name': attribute['name']})

                    attribute_value = self.env['product.attribute.value'].search(
                        [('name', '=', attribute['value']),('attribute_id', '=', attribute_odoo.id)], limit=1)

                    if not attribute_value:
                        attribute_value = self.env['product.attribute.value'].create({
                            'name': attribute['value'],
                            'attribute_id': attribute_odoo.id
                        })
                    variant_options_values_ids.append(attribute_value.id)

                    product_template_attribute_line = self.env['product.template.attribute.line'].search([('product_tmpl_id', '=', self.id), ('attribute_id', '=', attribute_odoo.id)],limit=1)

                    if not product_template_attribute_line:
                        self.env['product.template.attribute.line'].create({
                            'product_tmpl_id': self.id,
                            'attribute_id': attribute_odoo.id,
                            'value_ids': [Command.link(attribute_value.id)]
                        })
                    else:
                        product_template_attribute_line.value_ids = [Command.link(attribute_value.id)]

                current_product = self.env['product.product'].search([('product_tmpl_id','=', self.id)])
                current_product = current_product.filtered(lambda s: s.product_template_attribute_value_ids.product_attribute_value_id.ids == variant_options_values_ids),

                gelato_ref = variant['productUid']
                current_product[0].gelato_reference = gelato_ref

