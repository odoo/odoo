# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.fields import Command, Domain

from odoo.addons.sale_gelato import utils


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    gelato_template_ref = fields.Char(
        string="Gelato Template Reference", help="Synchronize to fetch variants from Gelato",
    )
    gelato_product_uid = fields.Char(
        string="Gelato Product UID",
        compute='_compute_gelato_product_uid',
        inverse='_inverse_gelato_product_uid',
        readonly=True,
    )
    gelato_image_ids = fields.One2many(
        string="Gelato Print Images",
        comodel_name='product.document',
        inverse_name='res_id',
        domain=[('is_gelato', '=', True)],
        readonly=True,
    )
    gelato_missing_images = fields.Boolean(
        string="Missing Print Images", compute='_compute_gelato_missing_images',
    )

    # === COMPUTE METHODS === #

    @api.depends('product_variant_ids.gelato_product_uid')
    def _compute_gelato_product_uid(self):
        self._compute_template_field_from_variant_field('gelato_product_uid')

    def _inverse_gelato_product_uid(self):
        self._set_product_variant_field('gelato_product_uid')

    @api.depends('gelato_image_ids')
    def _compute_gelato_missing_images(self):
        for product in self:
            product.gelato_missing_images = any(
                not image.datas for image in product.gelato_image_ids
            )

    # === ACTION METHODS === #

    def action_sync_gelato_template_info(self):
        """ Fetch the template information from Gelato and update the product template accordingly.

        :return: The action to display a toast notification to the user.
        :rtype: dict
        """
        # Fetch the template info from Gelato.
        try:
            endpoint = f'templates/{self.gelato_template_ref}'
            template_info = utils.make_request(
                self.env.company.sudo().gelato_api_key, 'ecommerce', 'v1', endpoint, method='GET'
            )  # In sudo mode to read the API key from the company.
        except UserError as e:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'type': 'danger',
                    'title': _("Could not synchronize with Gelato"),
                    'message': str(e),
                    'sticky': True,
                }
            }

        # Apply the necessary changes on the product template.
        self._create_attributes_from_gelato_info(template_info)
        self._create_print_images_from_gelato_info(template_info)

        # Display a toaster notification to the user if all went well.
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'type': 'success',
                'title': _("Successfully synchronized with Gelato"),
                'message': _("Missing product variants and images have been successfully created."),
                'sticky': False,
                'next': {
                    'type': 'ir.actions.client',
                    'tag': 'soft_reload'
                }
            }
        }

    # === BUSINESS METHODS === #

    def _create_attributes_from_gelato_info(self, template_info):
        """ Create attributes for the current product template.
        
        :param dict template_info: The template information fetched from Gelato.
        :return: None
        """
        if len(template_info['variants']) == 1:  # The template has no attribute.
            self.gelato_product_uid = template_info['variants'][0]['productUid']
        else:  # The template has multiple attributes.
            # Iterate over the variants to find and create the possible attributes.
            for variant_data in template_info['variants']:
                current_variant_pavs = self.env['product.attribute.value']
                for attribute_data in variant_data['variantOptions']:  # Attribute name and value.
                    # Search for the existing attribute with the proper variant creation policy and
                    # create it if not found.
                    attribute = self.env['product.attribute'].search(
                        [('name', '=', attribute_data['name']), ('create_variant', '=', 'always')],
                        limit=1,
                    )
                    if not attribute:
                        attribute = self.env['product.attribute'].create({
                            'name': attribute_data['name']
                        })

                    # Search for the existing attribute value and create it if not found.
                    attribute_value = self.env['product.attribute.value'].search([
                        ('name', '=', attribute_data['value']),
                        ('attribute_id', '=', attribute.id),
                    ], limit=1)
                    if not attribute_value:
                        attribute_value = self.env['product.attribute.value'].create({
                            'name': attribute_data['value'],
                            'attribute_id': attribute.id
                        })
                    current_variant_pavs += attribute_value

                    # Search for the existing PTAL and create it if not found.
                    ptal = self.env['product.template.attribute.line'].search(
                        [('product_tmpl_id', '=', self.id), ('attribute_id', '=', attribute.id)],
                        limit=1,
                    )
                    if not ptal:
                        self.env['product.template.attribute.line'].create({
                            'product_tmpl_id': self.id,
                            'attribute_id': attribute.id,
                            'value_ids': [Command.link(attribute_value.id)]
                        })
                    else:  # The PTAL already exists.
                        ptal.value_ids = [Command.link(attribute_value.id)]  # Link the value.

                # Find the variant that was automatically created and set the Gelato UID.
                for variant in self.product_variant_ids:
                    corresponding_ptavs = variant.product_template_attribute_value_ids
                    corresponding_pavs = corresponding_ptavs.product_attribute_value_id
                    if corresponding_pavs == current_variant_pavs:
                        variant.gelato_product_uid = variant_data['productUid']
                        break

            # Delete the incompatible variants that were created but not allowed by Gelato.
            variants_without_gelato = self.env['product.product'].search([
                ('product_tmpl_id', '=', self.id),
                ('gelato_product_uid', '=', False)
            ])
            variants_without_gelato.unlink()

    def _create_print_images_from_gelato_info(self, template_info):
        """ Create print image for the current product template.

        :param dict template_info: The template information fetched from Gelato.
        :return: None
        """
        # Iterate over the print image data listed in the info of the first variant, as we don't
        # support varying image placements between variants.
        for print_image_data in template_info['variants'][0]['imagePlaceholders']:
            # Gelato might send image placements that are named '1' or 'front' that are not accepted
            # by their API when placing order.
            if print_image_data['printArea'].lower() in ('1', 'front'):
                print_image_data['printArea'] = 'default'  # Use 'default' which is accepted.

            # Gelato might send several print images for the same placement if several layers were
            # defined, but we keep only one because their API only accepts one image per placement.
            print_image_found = bool(self.env['product.document'].search_count([
                ('name', 'ilike', print_image_data['printArea']),
                ('res_id', '=', self.id),
                ('res_model', '=', 'product.template'),
                ('is_gelato', '=', True),  # Avoid finding regular documents with the same name.
            ]))
            if not print_image_found:
                self.gelato_image_ids = [Command.create({
                    'name': print_image_data['printArea'].lower(),
                    'res_id': self.id,
                    'res_model': 'product.template',
                    'is_gelato': True,
                })]

    # === GETTER METHODS === #

    def _get_related_fields_variant_template(self):
        """ Override of `product` to add `gelato_product_uid` as a related field. """
        return super()._get_related_fields_variant_template() + ['gelato_product_uid']

    def _get_product_document_domain(self):
        """ Override of `product` to filter out gelato print images. """
        return super()._get_product_document_domain() & Domain('is_gelato', '=', False)
