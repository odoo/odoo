# Part of Odoo. See LICENSE file for full copyright and licensing details
import logging

from odoo import models, fields

logger = logging.getLogger(__name__)


class WebsiteGeneratorSale(models.Model):
    _inherit = 'website_generator.request'

    import_products = fields.Boolean("Import Products", default=True)

    def _get_call_params(self):
        data = super()._get_call_params()
        data['import_products'] = self.import_products
        return data

    def _create_model_records(self, tar, odoo_blocks):
        super()._create_model_records(tar, odoo_blocks)
        ecommerce_redirects = {}
        category_pages_redirects, created_categories_mapping = self._create_public_category_pages(tar, odoo_blocks)
        ecommerce_redirects.update(category_pages_redirects)
        product_redirects = self._create_products(tar, odoo_blocks, created_categories_mapping)
        ecommerce_redirects.update(product_redirects)
        odoo_blocks['direct_html_replacements_mapping'].update(ecommerce_redirects)

    def _create_products(self, tar, odoo_blocks, created_categories_mapping):
        # First extract all the product.template vals
        products = odoo_blocks.get('products', {})
        all_product_vals = []
        for page_name, product_data in products.items():
            # Create the product vals
            product_vals = {
                'name': product_data.get('name'),
                'list_price': product_data.get('price', '0'),
                'website_published': True,
                'description_ecommerce': product_data.get('description', ''),
                'website_id': self.website_id.id,
            }

            # Create the category and link it if needed
            category = None
            product_category = product_data.get('category')
            if product_category:
                category = self._find_or_create(
                    model='product.category',
                    domain=[('name', '=', product_category)],
                    vals={'name': product_category},
                )
                product_vals['categ_id'] = category.id

            all_product_vals.append(product_vals)

        # Create the product.templates
        created_products = self.env['product.template'].create(all_product_vals)

        # Get the images into base64 and create the product.image vals
        all_product_images = odoo_blocks['website'].get('all_product_images', {})
        all_image_vals = []
        product_redirects = {}
        for i, (page_name, product_data) in enumerate(products.items()):
            product_name = product_data.get('name')
            created_product = created_products[i]
            product_redirects[page_name] = created_product.website_url

            # Get product images and convert to base64
            images = product_data.get('images', [])
            images_info = self._get_image_info(tar, images, all_product_images)
            if not images_info:
                logger.warning('Error creating product: product %s has no images.', product_name)
                continue
            product_image = images_info[0]

            # Create the product featured image:
            created_product.image_1920 = product_image.get('base64')

            # Create the product image vals
            image_vals = [{
                'name': image_info.get('name'),
                'image_1920': image_info.get('base64'),
                'product_tmpl_id': created_product.id,
            } for image_info in images_info[1:]]
            all_image_vals += image_vals

        # Create the product.images.
        self.env['product.image'].create(all_image_vals)

        # Now we make the attributes and set the public category ids
        all_variant_image_vals = []
        for i, (page_name, product_data) in enumerate(products.items()):
            created_product = created_products[i]
            public_categ_ids = []
            for public_categ_name in product_data.get('public_categories', []):
                public_categ_id = created_categories_mapping.get(public_categ_name)
                if public_categ_id:
                    public_categ_ids.append(public_categ_id.id)
            created_product.write({
                'public_categ_ids': public_categ_ids,
            })
            all_variant_image_vals += self._manage_attributes(product_data, created_product, tar, all_product_images)

        self.env['product.image'].create(all_variant_image_vals)
        return product_redirects

    def _manage_attributes(self, product_dict, product, tar, all_product_images):
        attributes_values = product_dict.get('attributes_values', {})
        total_combinations = 1
        # Parse the available combinations
        for attribute_name, unique_values in attributes_values.items():
            # Avoid creating attributes with no values
            if not attribute_name:
                continue
            total_combinations *= len(unique_values)
            if total_combinations > 10000:
                break
            # Find or create the attribute
            attribute = self._find_or_create(
                model='product.attribute',
                domain=[('name', '=', attribute_name)],
                vals={'name': attribute_name},
            )

            # Find/create all the attribute values
            attribute_values = []
            for attr_value in unique_values:
                attribute_value = self._find_or_create(
                    model='product.attribute.value',
                    domain=[('name', '=', attr_value), ('attribute_id', '=', attribute.id)],
                    vals={'name': attr_value, 'attribute_id': attribute.id}
                )
                attribute_values.append(attribute_value.id)

            # Create the product_attribute_line
            self.env['product.template.attribute.line'].create({
                'attribute_id': attribute.id,
                'product_tmpl_id': product.id,
                'value_ids': attribute_values,
            })

        # Set the images for the variants
        all_variant_image_vals = []
        for variant in product.product_variant_ids:
            variant_names = variant.product_template_attribute_value_ids.mapped('name')
            variant_name = ' / '.join(sorted(variant_names))
            images = product_dict.get('variant_images', {}).get(variant_name, [])
            images_info = self._get_image_info(tar, images, all_product_images)
            if not images_info:
                continue
            variant.image_variant_1920 = images_info[0].get('base64')
            for image_info in images_info[1:]:
                all_variant_image_vals.append({
                    'name': image_info.get('name'),
                    'image_1920': images_info.get('base64'),
                    'product_variant_id': variant.id,
                })

        return all_variant_image_vals

    def _create_public_category_pages(self, tar, odoo_blocks):
        categories = odoo_blocks.get('categories', {})
        all_product_images = odoo_blocks['website'].get('all_product_images', {})
        all_category_vals = [{'name': category.get('name'), 'website_id': self.website_id.id} for category in categories.values()]
        created_category_pages = self.env['product.public.category'].create(all_category_vals)

        category_redirects = {}
        created_category_mapping = {}
        for i, (path, category) in enumerate(categories.items()):
            created_category = created_category_pages[i]
            created_category._compute_parents_and_self()
            created_category_mapping[created_category.name] = created_category
            category_redirects[path] = f'/shop/category/{self.env["ir.http"]._slug(created_category)}'
            # Get product images and convert to base64
            images = [category.get('image', '')]
            images_info = self._get_image_info(tar, images, all_product_images)
            if images_info:
                created_category.image_1920 = images_info[0].get('base64')

        return category_redirects, created_category_mapping
