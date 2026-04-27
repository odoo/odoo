import base64
import re

from collections import OrderedDict
from odoo import api, models, Command
from markupsafe import Markup
from odoo.addons.product_barcodelookup.tools import barcode_lookup_service
from odoo.tools import check_barcode_encoding

BARCODE_UOM_REGEX = r'^((?P<uom_val>(\d*\.?\d+))([\s?]*)(?P<unit>(([a-zA-Z]*))))$'


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    @api.onchange('barcode')
    def _onchange_barcode(self):
        for product in self:
            if self.env.user.has_group('base.group_system') and product.barcode and len(product.barcode) > 7:
                barcode_lookup_data = self.barcode_lookup(product.barcode)
                product._update_product_by_barcodelookup(product, barcode_lookup_data)

    def _to_float(self, value):
        try:
            return float(value or 0)
        except ValueError:
            return 0

    @api.model
    def _update_product_by_barcodelookup(self, product, barcode_lookup_data):
        product.ensure_one()
        imperial_len = self._get_volume_uom_id_from_ir_config_parameter() == self.env.ref('uom.product_uom_cubic_foot')
        imperial_weight = self._get_weight_uom_id_from_ir_config_parameter() == self.env.ref('uom.product_uom_lb')
        if not barcode_lookup_data:
            return
        products = barcode_lookup_data.get('products')
        # if no result or multi result ignore it
        if not products or len(products) > 1:
            return False
        product_data = products[0]

        if not product.name:
            product.name = product_data.get('title')

        # Image
        if not product.image_1920 and (images := product_data.get('images')):
            for image in images:
                img_response = barcode_lookup_service.barcode_lookup_request(image)
                if isinstance(img_response, dict):
                    # Response is not 200 when fetching the image so we just ignore it.
                    continue

                if img_response:
                    self._set_lookup_image(product, img_response)

        # Weight
        if not product.weight and (barcode_lookup_weight := product_data.get('weight', '')):
            if imperial_weight:
                convert_weight_uom = self.env.ref('uom.product_uom_kgm')
            else:
                convert_weight_uom = self.env.ref('uom.product_uom_lb')
            weight_re_match = re.match(BARCODE_UOM_REGEX, barcode_lookup_weight)
            if weight_re_match:
                weight_dict = weight_re_match.groupdict()
                weight = self._to_float(weight_dict.get('uom_val'))
                if weight_dict.get('unit') \
                        and self._get_weight_uom_id_from_ir_config_parameter().name != weight_dict['unit']:
                    weight = convert_weight_uom._compute_quantity(
                        weight,
                        to_unit=self._get_weight_uom_id_from_ir_config_parameter(),
                    )
                product.weight = weight

        # Price
        if (not self.list_price or self.list_price == 1.00) and (stores := product_data.get('stores')):
            for store in stores:
                price = self._to_float(store.get('price') or store.get('sale_price'))
                if store.get('currency') == self.currency_id.name:
                    product.list_price = self._get_list_price(price)
                    break
            else:
                product_currency_id = self.env['res.currency'].with_context(active_test=False).search([
                    ('name', '=', stores[0].get('currency')),
                ], limit=1)
                price = self._to_float(stores[0].get('price') or stores[0].get('sale_price'))
                if product_currency_id:
                    price = product_currency_id._convert(
                        price,
                        self.currency_id,
                    )
                product.list_price = self._get_list_price(price)

        # Attributes and values
        extra_attributes = {}
        if product._name == 'product.template' and self.env.user.has_group('product.group_product_variant') and not product.attribute_line_ids:
            attribute_lines = []
            for attr_name in ['color', 'gender', 'material', 'pattern', 'manufacturer', 'brand', 'size', 'age group']:
                attr_values = product_data.get(attr_name)
                if not attr_values:
                    continue
                attribute = self.env['product.attribute'].search([
                    ('name', 'ilike', attr_name),
                ], limit=1)
                if attribute:
                    for attr_value in attr_values.split(','):
                        attribute_value = self.env['product.attribute.value'].search([
                            ('name', 'ilike', attr_value.strip()),
                            ('attribute_id', '=', attribute.id)
                        ], limit=1)
                        if not (attribute_value or attr_name == 'color'):
                            attribute_value = self.env['product.attribute.value'].create({
                                'name': attr_value.strip().capitalize(),
                                'attribute_id': attribute.id,
                            })
                        if attribute_value:
                            attribute_lines.append(Command.create({
                                'attribute_id': attribute.id,
                                'value_ids': [Command.link(attribute_value.id)],
                            }))
                else:
                    extra_attributes.update({attr_name.capitalize(): attr_values})
            product.attribute_line_ids = attribute_lines

        # Product Categories
        if not product.id and (category := product_data.get('category')):
            sub_category = product_data.get('category', "").split('>')[-1].strip()
            if category := self.env['product.category'].search([('name', 'ilike', sub_category)], limit=1):
                product.categ_id = category

        # Dimensions and volume
        dimensions = {dim: (product_data.get(dim)) for dim in ['length', 'width', 'height']}
        uom_cm = self.env.ref('uom.product_uom_cm')
        uom_m = self.env.ref('uom.product_uom_meter')
        uom_in = self.env.ref('uom.product_uom_inch')
        uom_foot = self.env.ref('uom.product_uom_foot')

        convert_volume_uom = False
        for dim_name, dimension in dimensions.items():
            re_match = re.match(BARCODE_UOM_REGEX, dimension)
            dim_value = 1
            if re_match:
                dim_dict = re_match.groupdict()
                dim_value = self._to_float(dim_dict.get('uom_val'))
                # convert value to correct uom
                if dim_dict.get('unit'):
                    if dim_dict['unit'] == 'cm' and imperial_len:
                        dimensions[dim_name] = uom_cm._compute_quantity(dim_value, to_unit=uom_in)
                        convert_volume_uom = self.env.ref('uom.product_uom_cubic_meter')
                    if dim_dict['unit'] == 'in' and not imperial_len:
                        dimensions[dim_name] = uom_in._compute_quantity(dim_value, to_unit=uom_cm)
                        convert_volume_uom = self.env.ref('uom.product_uom_cubic_foot')
            dimensions[dim_name] = dim_value

        volume = 1 if re_match else 0
        for dim_value in dimensions.values():
            if imperial_len:
                dim_value = uom_in._compute_quantity(dim_value, uom_foot)
            else:
                dim_value = uom_cm._compute_quantity(dim_value, uom_m)
            volume *= dim_value

        if convert_volume_uom:
            product.volume = convert_volume_uom._compute_quantity(
                volume,
                to_unit=self._get_volume_uom_id_from_ir_config_parameter()
            )
        else:
            product.volume = volume

        # Description
        product_description = OrderedDict()
        if category := product_data.get("category"):
            product_description.update({"Category": Markup("<li>%s</li>") % category})
        if features_data := product_data.get('features'):
            product_description.update({"Features": Markup('').join([Markup("<li>%s</li>") % (feature) for feature in features_data])})
        for parameter in ['mpn', 'model', 'asin', 'weight']:
            if para_val := product_data.get(parameter):
                extra_attributes.update({parameter.capitalize(): para_val})
        if product_data.get("length") or product_data.get("width") or product_data.get("height"):
            dimension_data = ""
            if product_data.get("length"):
                dimension_data += f"{product_data['length']} (L) "
            if product_data.get("width"):
                dimension_data += f"{product_data['width']} (W) "
            if product_data.get("height"):
                dimension_data += f"{product_data['height']} (H)"
            extra_attributes.update({"Dimension": dimension_data})
        if extra_attributes.items():
            product_description.update({"Attributes": Markup("").join([Markup("<li>%s: %s</li>") % (attr_name, attr_value) for attr_name, attr_value in extra_attributes.items()])})

        if description := product_data.get('description'):
            product.description = Markup("<p>%s</p>") % description
        elif not product.description:
            product.description = ""
        product.description += Markup("<br>").join([Markup("<b>%s</b><br><ul>%s</ul>") % (attr_name, attr_value)
                                                    for attr_name, attr_value in product_description.items() if attr_value])
        return description

    @api.model
    def barcode_lookup(self, barcode=False):
        api_key = barcode_lookup_service.get_barcode_lookup_key(self)
        if not api_key:
            return False
        if barcode and not self.env.context.get("skip_barcode_check", False) \
                and not any(check_barcode_encoding(barcode, enc) for enc in ("upca", "ean8", "ean13")):
            return False
        params = {'barcode': barcode, 'key': api_key}
        response = barcode_lookup_service.barcode_lookup_request('https://api.barcodelookup.com/v3/products', params)
        return response.json() if not isinstance(response, dict) else response

    @api.model_create_multi
    def create(self, vals_list):
        products = super().create(vals_list)
        for product, vals in zip(products, vals_list):
            if 'is_published' in product and 'is_published' not in vals and not self._context.get('website_published') and product.public_categ_ids:
                product.is_published = True
            if 'available_in_pos' in product and not self._context.get('can_be_sold') and product.pos_categ_ids:
                product.available_in_pos = True
        return products

    def copy_data(self, default=None):
        vals_list = super().copy_data(default)
        if 'is_published' in self:
            for vals in vals_list:
                vals['is_published'] = False
        return vals_list

    def _set_lookup_image(self, product, img):
        image = base64.b64encode(img.content)
        if not product.image_1920:
            product.image_1920 = image
            return True
        return image
