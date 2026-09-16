# -*- coding: utf-8 -*-
import imghdr
import urllib
import base64
import requests
import json
import itertools
import logging
import time
from woocommerce import API
from urllib.request import urlopen
from odoo.exceptions import UserError
from odoo import models, api, fields, _
from odoo.tools import config
from bs4 import BeautifulSoup
import datetime
import re


config['limit_time_real'] = 1000000


_logger = logging.getLogger(__name__)

class WooProductImage(models.Model):
    _name = 'woo.product.image'
    _description = 'woo.product.image'

    name = fields.Char()
    product_id = fields.Many2one('product.product', ondelete='cascade')
    template_id = fields.Many2one('product.template', string='Product template', ondelete='cascade')
    image = fields.Image()
    url = fields.Char(string="Image URL", help="External URL of image")

    @api.onchange('url')
    def validate_img_url(self):
        if self.url:
            try:
                image_types = ["image/jpeg", "image/png", "image/tiff", "image/vnd.microsoft.icon", "image/x-icon",
                               "image/vnd.djvu", "image/svg+xml", "image/gif"]
                response = urllib.request.urlretrieve(self.url)

                if response[1].get_content_type() not in image_types:
                    raise UserError(_("Please provide valid Image URL with any extension."))
                else:
                    photo = base64.encodebytes(urlopen(self.url).read())
                    self.image = photo

            except Exception as error:
                raise UserError(_("Invalid Url"))


class ProductProduct(models.Model):
    _inherit = 'product.product'

    woo_id = fields.Char('WooCommerce ID')
    woo_regular_price = fields.Float('WooCommerce Regular Price')
    #DB woo_product_weight = fields.Float("Woo Weight")
    # woo_product_length = fields.Float("Woo Length")
    # woo_product_width = fields.Float("Woo Width")
    # woo_product_height = fields.Float("Woo Height")
    # woo_weight_unit = fields.Char(compute='_compute_weight_uom_name')
    # woo_unit_other = fields.Char(compute='_compute_length_uom_name')
    is_exported = fields.Boolean('Synced In Woocommerce', default=False)
    woo_instance_id = fields.Many2one('woo.instance', ondelete='cascade')
    woo_varient_description = fields.Text('Woo Variant Description')
    default_code = fields.Char('Internal Reference', index=True, required=False)
    woo_sale_price = fields.Float('WooCommerce Sales Price')
    wps_subtitle = fields.Char(string="Woo wps subtitle")

    def export_selected_product_variant(self, instance_id):
        location = instance_id.url
        cons_key = instance_id.client_id
        sec_key = instance_id.client_secret
        version = 'wc/v3'

        wcapi = API(url=location, consumer_key=cons_key, consumer_secret=sec_key, version=version)

        selected_ids = self.env.context.get('active_ids', [])
        selected_records = self.env['product.product'].sudo().browse(selected_ids)
        all_records = self.env['product.product'].sudo().search([])
        if selected_records:
            records = selected_records
        else:
            records = all_records

        list = []
        for rec in records:
            attributes_lst = []

            if rec.product_tmpl_id.woo_id and rec.product_template_attribute_value_ids:
                for combinations in rec.product_template_attribute_value_ids:
                    dict_attr = {}
                    dict_attr['id'] = combinations.attribute_id.woo_id
                    dict_attr['name'] = combinations.attribute_id.name
                    dict_attr['option'] = combinations.name
                    attributes_lst.append(dict_attr)

            data = {
                "id": rec.woo_id if rec.woo_id else '',
                "name": rec.product_tmpl_id.woo_id,
                "sku": rec.default_code if rec.default_code else '',
                "regular_price": str(rec.woo_regular_price) if rec.woo_regular_price else '',
                "sale_price": str(rec.woo_sale_price),
                "manage_stock": True,
                "stock_quantity": rec.qty_available,
                "description": str(rec.woo_varient_description) if rec.woo_varient_description else '',
                "weight": str(rec.woo_product_weight) if rec.woo_product_weight else '',
                "dimensions":
                    {
                        "length": str(rec.woo_product_length) if rec.woo_product_length else '',
                        "width": str(rec.woo_product_width) if rec.woo_product_width else '',
                        "height": str(rec.woo_product_height) if rec.woo_product_height else '',
                    },
                "attributes": attributes_lst,
            }

            if data.get('id'):
                try:
                    parsed_data = wcapi.post("products/%s/variations/%s" % (data.get('name'), data.get('id')), data)
                    if parsed_data.status_code != 200:
                        message = parsed_data.json().get('message')
                        self.env['bus.bus']._sendone(self.env.user.partner_id, 'snailmail_invalid_address', {
                            'title': _("Failed"),
                            'message': _(message),
                        })
                except Exception as error:
                    raise UserError(_("Please check your connection and try again"))
            else:
                try:
                    data.pop('id')
                    parsed_data = wcapi.post("products/%s/variations" % (int(data.get('name'))), data)
                    if parsed_data.status_code != 200:
                        parsed_data = parsed_data.json()
                        if parsed_data:
                            rec.write({
                                'woo_id': parsed_data.get('id'),
                                'is_exported': True,
                                'woo_instance_id': instance_id.id,
                            })
                        message = parsed_data.get('message')
                        self.env['bus.bus'].sendone((self._cr.dbname, 'res.partner', self.env.user.partner_id.id), {
                            'type': 'snailmail_invalid_address', 'title': _("Failed"),
                            'message': _(message)
                        })
                except Exception as error:
                    raise UserError(_("Please check your connection and try again"))

        # self.env['product.template'].import_product(instance_id)


class Product(models.Model):
    _inherit = 'product.template'

    woo_id = fields.Char('WooCommerce ID')
    woo_regular_price = fields.Float('WooCommerce Regular Price')
    woo_sale_price = fields.Float('WooCommerce Sale Price')
    commission_type = fields.Selection([
        ('global', 'Global'),
        ('percent', 'Percentage'),
        ('fixed', 'Fixed'),
        ('percent_fixed', 'Percent Fixed'),
    ], "Commission Type")
    commission_value = fields.Float("Commission for Admin")
    fixed_commission_value = fields.Float("Fixed Price")
    woo_product_weight = fields.Float("Woo Weight")
    woo_product_length = fields.Float("Woo Length")
    woo_product_width = fields.Float("Woo Width")
    woo_product_height = fields.Float("Woo Height")
    woo_weight_unit = fields.Char(compute='_compute_weight_uom_name')
    woo_unit_other = fields.Char(compute='_compute_length_uom_name')
    website_published = fields.Boolean()
    woo_image_ids = fields.One2many("woo.product.image", "template_id")
    woo_tag_ids = fields.Many2many("product.tag.woo", relation='product_woo_tags_rel', string="Tags")
    is_exported = fields.Boolean('Synced In Woocommerce', default=False)
    woo_instance_id = fields.Many2one('woo.instance', ondelete='cascade')
    woo_product_qty = fields.Float("Woo Stock Quantity")
    woo_short_description = fields.Html(string="Product Short Description")
    woo_ingredients = fields.Html(string="Ingredients")
    woo_details = fields.Html(string="Details")
    woo_instructions = fields.Html(string="Instructions")
    woo_scientific_ref = fields.Html(string="Scientific References")
    product_category_ids = fields.Many2many("product.category", relation='product_temp_category_rel', string="Categories")
    woo_product_videos = fields.Text("Product Videos")
    wps_subtitle = fields.Char(string="Woo wps subtitle")
    woo_product_attachment = fields.Binary(string="WooCommerce Attachment")

    @api.model
    def _get_volume_uom_id_from_ir_config_parameter(self):
        """ Get the unit of measure to interpret the `volume` field. By default, we consider
        that volumes are expressed in cubic meters. Users can configure to express them in cubic feet
        by adding an ir.config_parameter record with "product.volume_in_cubic_feet" as key
        and "1" as value.
        """
        product_length_in_feet_param = self.env['ir.config_parameter'].sudo().get_param('product.volume_in_cubic_feet')
        if product_length_in_feet_param == '1':
            return self.env.ref('uom.product_uom_cubic_foot')
        else:
            return self.env.ref('uom.product_uom_cubic_inch')

    def _compute_weight_uom_name(self):
        self.woo_weight_unit = self._get_weight_uom_name_from_ir_config_parameter()
        return super(Product, self)._compute_weight_uom_name()

    @api.model
    def _get_length_uom_id_from_ir_config_parameter(self):
        """ Get the unit of measure to interpret the `length`, 'width', 'height' field.
        By default, we considerer that length are expressed in millimeters. Users can configure
        to express them in feet by adding an ir.config_parameter record with "product.volume_in_cubic_feet"
        as key and "1" as value.
        """
        product_length_in_feet_param = self.env['ir.config_parameter'].sudo().get_param('product.volume_in_cubic_feet')
        if product_length_in_feet_param == '1':
            return self.env.ref('uom.product_uom_foot')
        else:
            return self.env.ref('uom.product_uom_inch')

    def _compute_length_uom_name(self):
        self.woo_unit_other = self._get_length_uom_name_from_ir_config_parameter()

    def woo_published(self):
        location = self.woo_instance_id.url
        cons_key = self.woo_instance_id.client_id
        sec_key = self.woo_instance_id.client_secret
        version = 'wc/v3'

        wcapi = API(url=location, consumer_key=cons_key, consumer_secret=sec_key, version=version)
        if self.woo_id:
            try:
                wcapi.post("products/%s" % self.woo_id, {'status': 'publish'}).json()
                self.sudo().write({'website_published': True})
            except Exception as error:
                raise UserError(
                    _("Something went wrong while updating Product.\n\nPlease Check your Connection \n\n" + str(error)))
        return True

    def woo_unpublished(self):
        location = self.woo_instance_id.url
        cons_key = self.woo_instance_id.client_id
        sec_key = self.woo_instance_id.client_secret
        version = 'wc/v3'

        wcapi = API(url=location, consumer_key=cons_key, consumer_secret=sec_key, version=version)
        if self.woo_id:
            try:
                wcapi.post("products/%s" % self.woo_id, {'status': 'draft'}).json()
                self.sudo().write({'website_published': False})
            except Exception as error:
                raise UserError(
                    _("Something went wrong while updating Product.\n\nPlease Check your Connection \n\n" + str(error)))
        return True

    def cron_export_product(self):
        all_instances = self.env['woo.instance'].sudo().search([])
        for rec in all_instances:
            if rec:
                self.env['product.template'].export_selected_product(rec)

    def export_selected_product(self, instance_id):
        location = instance_id.url
        cons_key = instance_id.client_id
        sec_key = instance_id.client_secret
        version = 'wc/v3'

        wcapi = API(url=location, consumer_key=cons_key, consumer_secret=sec_key, version=version)

        selected_ids = self.env.context.get('active_ids', [])
        selected_records = self.env['product.template'].sudo().browse(selected_ids)
        all_records = self.env['product.template'].sudo().search([])
        if selected_records:
            records = selected_records
        else:
            records = all_records

        list = []
        for rec in records:
            attrs = []
            tags_list = []

            if rec.woo_tag_ids:
                for tag in rec.woo_tag_ids:
                    tags_list.append({'name': tag.name})

            if rec.attribute_line_ids:
                for att in rec.attribute_line_ids:
                    if att.attribute_id.woo_id:
                        values = []
                        for val in att.value_ids:
                            values.append(val.name)

                        attrs.append({
                            'id': att.attribute_id.woo_id,
                            'name': att.attribute_id.name,
                            'slug': att.attribute_id.slug,
                            'options': values,
                        })

            images = []
            for img in rec.woo_image_ids:
                images.append({
                    "src": img.url,
                })

            data = {
                "id": rec.woo_id,
                "name": rec.name,
                "sku": rec.default_code if rec.default_code else '',
                "regular_price": str(rec.woo_regular_price) if rec.woo_regular_price else '',
                "sale_price": str(rec.woo_sale_price),
                "manage_stock": True,
                "stock_quantity": rec.qty_available,
                "description": str(rec.description) if rec.description else '',
                "categories": [
                    {
                        "id": int(rec.categ_id.woo_id)
                    },
                ],
                "tags": tags_list,
                "purchaseable": rec.purchase_ok,
                "on_sale": rec.sale_ok,
                "weight": str(rec.woo_product_weight) if rec.woo_product_weight else '',
                "dimensions":
                    {
                        "length": str(rec.woo_product_length) if rec.woo_product_length else '',
                        "width": str(rec.woo_product_width) if rec.woo_product_width else '',
                        "height": str(rec.woo_product_height) if rec.woo_product_height else '',
                    },
                "attributes": attrs,
            }
            if images:
                data["images"] = images

            if data.get('id'):
                try:
                    _logger.info('%s', wcapi.post("products/%s" % (data.get('id')), data).json())
                except Exception as error:
                    raise UserError(_("Please check your connection and try again"))
            else:
                try:
                    _logger.info('%s', wcapi.post("products", data).json())
                    parsed_data = wcapi.post("products", data).json()
                    if parsed_data:
                        rec.write({
                            'woo_id': parsed_data.get('id'),
                            'is_exported': True,
                            'woo_instance_id': instance_id.id,
                        })
                except Exception as error:
                    raise UserError(_("Please check your connection and try again"))

        # self.import_product(instance_id)

    def cron_import_product(self):
        all_instances = self.env['woo.instance'].sudo().search([])
        for rec in all_instances:
            if rec:
                self.env['product.template'].import_product(rec)

    def import_product(self, instance_id):
        page = 1
        while page > 0:
            location = instance_id.url
            cons_key = instance_id.client_id
            sec_key = instance_id.client_secret
            version = 'wc/v3'

            wcapi = API(url=location,
                        consumer_key=cons_key,
                        consumer_secret=sec_key,
                        version=version,
                        timeout=900
                        )

            url = "products"
            try:
                data = wcapi.get(url, params={'orderby': 'id', 'order': 'asc','per_page': 100, 'page': page})
                page += 1

            except Exception as error:
                time.sleep(5)
                continue
                # raise UserError(_("Please check your connection and try again"))
            if data.status_code == 200:
                if data.content:
                    parsed_data = data.json()
                    if len(parsed_data) == 0:
                        page = 0
                    if parsed_data:
                        for ele in parsed_data:
                            ''' This will avoid duplications of products already
                            having woo_id.
                            '''
                            pro_t = []
                            categ_list = []
                            if ele.get('sku'):
                                product = self.env['product.template'].sudo().search(['|', ('woo_id', '=', ele.get('id')), ('default_code', '=', ele.get('sku'))], limit=1)
                            else:
                                product = self.env['product.template'].sudo().search([('woo_id', '=', ele.get('id'))],limit=1)

                            ''' This is used to update woo_id of a product, this
                            will avoid duplication of product while syncing product.
                            '''
                            product_without_woo_id = self.env['product.template'].sudo().search([('woo_id', '=', False), ('default_code', '=', ele.get('sku'))], limit=1)

                            product_product_without_id = self.env['product.product'].sudo().search([('product_tmpl_id', '=', product_without_woo_id.id)], limit=1)

                            dict_p = {}
                            dict_p['is_exported'] = True
                            dict_p['woo_instance_id'] = instance_id.id
                            dict_p['company_id'] = instance_id.woo_company_id.id
                            dict_p['woo_id'] = ele.get('id') if ele.get('id') else ''
                            dict_p['website_published'] = True if ele.get('status') and ele.get('status') == 'publish' else False
                            dict_p['name'] = ele.get('name') if ele.get('name') else ''
                            if ele.get('description'):
                                parsed_desc = ele.get('description').replace('<h1>', '<h6>').replace('</h1>', '</h6>')
                                parsed_desc = parsed_desc.replace('<h2>', '<h6>').replace('</h2>', '</h6>')
                                parsed_desc = parsed_desc.replace('<h3>', '<h6>').replace('</h3>', '</h6>')
                                dict_p['description'] = parsed_desc
                                soup = BeautifulSoup(ele.get('description'), 'html.parser')
                                description_converted_to_text = soup.get_text()
                                dict_p['description_sale'] = ele.get('sku') + " " + ele.get('name')
                            dict_p['default_code'] = ele.get('sku') if ele.get('sku') else ''

                            for rec in ele.get('categories'):
                                categ = self.env['product.category'].sudo().search([('woo_id', '=', rec.get('id'))], limit=1)
                                if categ and categ.id not in categ_list:
                                    categ_list.append(categ.id)
                            if ele.get('categories') and ele.get('categories')[0].get('name'):
                                categ = self.env['product.category'].sudo().search([('name', '=', ele.get('categories')[0].get('name'))], limit=1)
                                if categ:
                                    dict_p['categ_id'] = categ[0].id

                            dict_p['list_price'] = ele.get('price') if ele.get('price') else 0.0
                            dict_p['woo_sale_price'] = ele.get('price') if ele.get('price') else 0.0
                            dict_p['woo_regular_price'] = ele.get('price') if ele.get('price') else 0.0
                            dict_p['purchase_ok'] = True #if ele.get('purchaseable') and ele.get('purchaseable') == True else True
                            dict_p['sale_ok'] = True #if ele.get('on_sale') and ele.get('on_sale') == True else False
                            dict_p['qty_available'] = True if ele.get('stock_quantity') else 0.00

                            if ele.get('images'):
                                url = ele.get('images')[0].get('src')
                                response = requests.get(url)
                                if imghdr.what(None, response.content) != 'webp':
                                    image = base64.b64encode(requests.get(url).content)
                                    dict_p['image_1920'] = image

                            dict_p['weight'] = float(ele.get('weight')) if ele.get('weight') else 0.00
                            dict_p['woo_product_weight'] = float(ele.get('weight')) if ele.get('weight') else 0.00
                            dict_p['woo_product_length'] = float(ele.get('dimensions').get('length'))  if ele.get('dimensions') and ele.get('dimensions').get('length') else 0.00
                            dict_p['woo_product_width'] = float(ele.get('dimensions').get('width')) if ele.get('dimensions') and ele.get('dimensions').get('width') else 0.00
                            dict_p['woo_product_height'] = float(ele.get('dimensions').get('height')) if ele.get('dimensions') and ele.get('dimensions').get('height') else 0.00

                            if ele.get('tags'):
                                for rec in ele.get('tags'):
                                    existing_tag = self.env['product.tag.woo'].sudo().search(['|', ('woo_id', '=', rec.get('id')), ('name', '=', rec.get('name'))], limit=1)
                                    dict_value = {}
                                    dict_value['is_exported'] = True
                                    dict_value['woo_instance_id'] = instance_id.id
                                    dict_value['name'] = rec.get('name') if rec.get('name') else ''
                                    dict_value['woo_id'] = rec.get('id') if rec.get('id') else ''
                                    dict_value['description'] = rec.get('description') if rec.get('description') else ''
                                    dict_value['slug'] = rec.get('slug') if rec.get('slug') else ''

                                    if not existing_tag:
                                        create_tag_value = self.env['product.tag.woo'].sudo().create(dict_value)
                                        pro_t.append(create_tag_value.id)
                                    else:
                                        write_tag_value = existing_tag.sudo().write(dict_value)
                                        pro_t.append(existing_tag.id)

                            if not product and product_without_woo_id:
                                product_without_woo_id.sudo().write(dict_p)
                                if product_product_without_id and not ele.get('variations'):
                                    product_product_without_id.sudo().write({
                                        'is_exported': True,
                                        'woo_id': dict_p['woo_id'],
                                        'woo_sale_price': product_without_woo_id.woo_sale_price,
                                        'default_code':ele.get('sku'),
                                        'qty_available':dict_p['qty_available']
                                    })

                            if product and not product_without_woo_id:
                                product.sudo().write(dict_p)

                            if not product and not product_without_woo_id:
                                dict_p['type'] = 'product'
                                '''If product is not present we create it'''
                                pro_create = self.env['product.template'].create(dict_p)
                                product_product_vr = self.env['product.product'].sudo().search(
                                    [('product_tmpl_id', '=', pro_create.id)])
                                if product_product_vr and not ele.get('variations'):
                                    product_product_vr.sudo().write({
                                        'is_exported': True,
                                        'woo_id': dict_p['woo_id'],
                                        'woo_sale_price': pro_create.woo_sale_price,
                                        'default_code': ele.get('sku'),
                                        'qty_available': dict_p['qty_available']
                                    })
                                if pro_t:
                                    pro_create.woo_tag_ids = [(4, val) for val in pro_t]

                                if pro_create:
                                    for rec in ele.get('meta_data'):
                                        if rec.get('key') == '_wcfm_product_author':
                                            vendor_id = rec.get('value')
                                            vendor_odoo_id = self.env['res.partner'].sudo().search([('woo_id', '=', vendor_id)],
                                                                                            limit=1)
                                            if vendor_odoo_id:
                                                seller = self.env['product.supplierinfo'].sudo().create({
                                                    'name': vendor_odoo_id.id,
                                                    'product_id': pro_create.id
                                                })
                                                pro_create.seller_ids = [(6, 0, [seller.id])]

                                        if rec.get('key') == '_wcfmmp_commission':
                                            pro_create.commission_type = rec.get('value').get('commission_mode')
                                            if pro_create.commission_type == 'percent':
                                                pro_create.commission_value = rec.get('value').get('commission_percent')
                                            elif pro_create.commission_type == 'fixed':
                                                pro_create.fixed_commission_value = rec.get('value').get('commission_fixed')
                                            elif pro_create.commission_type == 'percent_fixed':
                                                pro_create.commission_value = rec.get('value').get('commission_percent')
                                                pro_create.fixed_commission_value = rec.get('value').get('commission_fixed')

                                    if ele.get('attributes'):
                                        dict_attr = {}
                                        for rec in ele.get('attributes'):
                                            product_attr = self.env['product.attribute'].sudo().search(
                                                ['|', ('woo_id', '=', rec.get('id')), ('name', '=', rec.get('name'))],
                                                limit=1)
                                            dict_attr['is_exported'] = True
                                            dict_attr['woo_instance_id'] = instance_id.id
                                            dict_attr['woo_id'] = rec.get('id') if rec.get('id') else ''
                                            dict_attr['name'] = rec.get('name') if rec.get('name') else ''
                                            dict_attr['slug'] = rec.get('slug') if rec.get('slug') else ''
                                            if not product_attr:
                                                product_attr = self.env['product.attribute'].sudo().create(dict_attr)

                                            pro_val = []
                                            if rec.get('options'):
                                                for value in rec.get('options'):
                                                    existing_attr_value = self.env['product.attribute.value'].sudo().search(
                                                        [('name', '=', value),('attribute_id','=',product_attr.id)], limit=1)
                                                    dict_value = {}
                                                    dict_value['is_exported'] = True
                                                    dict_value['woo_instance_id'] = instance_id.id
                                                    dict_value['name'] = value if value else ''
                                                    dict_value['attribute_id'] = product_attr.id

                                                    if not existing_attr_value and dict_value['attribute_id']:
                                                        create_value = self.env['product.attribute.value'].sudo().create(
                                                            dict_value)
                                                        pro_val.append(create_value.id)
                                                    elif existing_attr_value:
                                                        write_value = existing_attr_value.sudo().write(
                                                            dict_value)
                                                        pro_val.append(existing_attr_value.id)

                                            if product_attr:
                                                if pro_val:
                                                    exist = self.env['product.template.attribute.line'].sudo().search(
                                                        [('attribute_id', '=', product_attr.id),
                                                         ('value_ids', 'in', pro_val),
                                                         ('product_tmpl_id', '=', pro_create.id)], limit=1)
                                                    if not exist:
                                                        create_attr_line = self.env[
                                                            'product.template.attribute.line'].sudo().create({
                                                            'attribute_id': product_attr.id,
                                                            'value_ids': [(6, 0, pro_val)],
                                                            'product_tmpl_id': pro_create.id
                                                        })
                                                    else:
                                                        exist.sudo().write({
                                                            'attribute_id': product_attr.id,
                                                            'value_ids': [(6, 0, pro_val)],
                                                            'product_tmpl_id': pro_create.id
                                                        })

                                    if ele.get('variations'):
                                        url = location + '/wp-json/wc/v3'
                                        consumer_key = cons_key
                                        consumer_secret = sec_key
                                        session = requests.Session()
                                        session.auth = (consumer_key, consumer_secret)
                                        product_id = ele.get('id')
                                        endpoint = f"{url}/products/{product_id}/variations"
                                        response = session.get(endpoint)
                                        if response.status_code == 200:
                                            parsed_variants_data = json.loads(response.text)
                                            variant_list = []
                                            product_variant = self.env['product.product'].sudo().search(
                                                [('product_tmpl_id', '=', pro_create.id)])

                                            lines_without_no_variants = pro_create.valid_product_template_attribute_line_ids._without_no_variant_attributes()
                                            all_variants = pro_create.with_context(
                                                active_test=False).product_variant_ids.sorted(
                                                lambda p: (p.active, -p.id))
                                            single_value_lines = lines_without_no_variants.filtered(
                                                lambda ptal: len(ptal.product_template_value_ids._only_active()) == 1)
                                            if single_value_lines:
                                                for variant in all_variants:
                                                    combination = variant.product_template_attribute_value_ids | single_value_lines.product_template_value_ids._only_active()

                                            all_combinations = itertools.product(*[
                                                ptal.product_template_value_ids._only_active() for ptal in
                                                lines_without_no_variants
                                            ])

                                            if parsed_variants_data:
                                                for variant in parsed_variants_data:
                                                    list_1 = []
                                                    for var in variant.get('attributes'):
                                                        list_1.append(var.get('option'))
                                                    for item in product_variant:
                                                        if item.product_template_attribute_value_ids:
                                                            list_values = []
                                                            for rec in item.product_template_attribute_value_ids:
                                                                if list_1 and rec.name == list_1[0]:
                                                                    price_extra = item.lst_price - float(variant.get('sale_price')) if variant.get('sale_price') else item.lst_price - float(variant.get('regular_price'))
                                                                    if price_extra >= 0:
                                                                        rec.price_extra = price_extra
                                                                    else:
                                                                        rec.price_extra = -(price_extra)
                                                                list_values.append(rec.name)
                                                            if set(list_1).issubset(list_values):
                                                                item.default_code = variant.get('sku')
                                                                item.woo_sale_price = variant.get('sale_price') if variant.get('sale_price') else variant.get('regular_price')
                                                                item.woo_regular_price = variant.get('regular_price')
                                                                item.woo_id = variant.get('id')
                                                                item.woo_instance_id = instance_id
                                                                item.qty_available = variant.get('stock_quantity')
                                                                item.woo_product_weight = variant.get('weight')
                                                                item.weight = variant.get('weight')
                                                                item.is_exported = True
                                                                if variant.get('dimensions'):
                                                                    if variant.get('dimensions').get('length'):
                                                                        item.woo_product_length = variant.get('dimensions').get('length')
                                                                    if variant.get('dimensions').get('width'):
                                                                        item.woo_product_width = variant.get('dimensions').get('width')
                                                                    if variant.get('dimensions').get('height'):
                                                                        item.woo_product_height = variant.get('dimensions').get('height')
                                                                    item.volume = item.woo_product_length * item.woo_product_width * item.woo_product_height
                                                                if variant.get('description'):
                                                                    item.woo_varient_description = variant.get(
                                                                        'description').replace('<p>', '').replace('</p>',
                                                                                                                  '')
                                                                    item.description = variant.get('description')
                                                                    # item.description_sale = variant.get('description').replace('<p>', '').replace('</p>', '')
                                                                    item.description_sale = item.name
                                                                # else:
                                                                #     item.description = item.name
                                                for combination_tuple in all_combinations:
                                                    combination = self.env['product.template.attribute.value'].concat(
                                                        *combination_tuple)
                                                    list_var = []
                                                    for n in combination:
                                                        list_var.append(n.name)

                                    pro_create.default_code = ele.get('sku')
                                self.env.cr.commit()
                            else:
                                product = product or product_without_woo_id
                                pro_create = product.sudo().write(dict_p)

                                product_product = self.env['product.product'].sudo().search(
                                    [('product_tmpl_id', '=', product.id)], limit=1)
                                if product_product and not ele.get('variations'):
                                    product_product.sudo().write({
                                        'is_exported': True,
                                        'woo_id': dict_p['woo_id'],
                                        'woo_sale_price': product.woo_sale_price,
                                        'default_code': dict_p['default_code'],
                                        'qty_available': dict_p['qty_available']

                                    })

                                if pro_t:
                                    product.woo_tag_ids = [(4, val) for val in pro_t]

                                if ele.get('attributes'):
                                    dict_attr = {}
                                    for rec in ele.get('attributes'):
                                        product_attr = self.env['product.attribute'].sudo().search(['|', ('woo_id', '=', rec.get('id')), ('name', '=', rec.get('name'))],limit=1)
                                        dict_attr['is_exported'] = True
                                        dict_attr['woo_instance_id'] = instance_id.id
                                        dict_attr['woo_id'] = rec.get('id') if rec.get('id') else ''
                                        dict_attr['name'] = rec.get('name') if rec.get('name') else ''
                                        dict_attr['slug'] = rec.get('slug') if rec.get('slug') else ''
                                        if not product_attr:
                                            product_attr = self.env['product.attribute'].sudo().create(dict_attr)

                                        pro_val = []
                                        if rec.get('options'):
                                            for value in rec.get('options'):
                                                existing_attr_value = self.env['product.attribute.value'].sudo().search(
                                                    [('name', '=', value),('attribute_id','=',product_attr.id)], limit=1)
                                                dict_value = {}
                                                dict_value['is_exported'] = True
                                                dict_value['woo_instance_id'] = instance_id.id
                                                dict_value['name'] = value if value else ''
                                                dict_value['attribute_id'] = product_attr.id

                                                if not existing_attr_value and dict_value['attribute_id']:
                                                    create_value = self.env['product.attribute.value'].sudo().create(dict_value)
                                                    pro_val.append(create_value.id)

                                                elif existing_attr_value:
                                                    write_value = self.env['product.attribute.value'].sudo().write(dict_value)
                                                    pro_val.append(existing_attr_value.id)

                                        if product_attr:
                                            if pro_val:
                                                exist = self.env['product.template.attribute.line'].sudo().search(
                                                    [('attribute_id', '=', product_attr.id), ('value_ids', 'in', pro_val),
                                                     ('product_tmpl_id', '=', product.id)], limit=1)
                                                if not exist:
                                                    create_attr_line = self.env['product.template.attribute.line'].sudo().create(
                                                        {'attribute_id': product_attr.id, 'value_ids': [(6, 0, pro_val)],
                                                         'product_tmpl_id': product.id})
                                                else:
                                                    exist.sudo().write(
                                                        {'attribute_id': product_attr.id, 'value_ids': [(6, 0, pro_val)],
                                                         'product_tmpl_id': product.id})

                                if ele.get('variations'):
                                    url = location + '/wp-json/wc/v3'
                                    consumer_key = cons_key
                                    consumer_secret = sec_key
                                    session = requests.Session()
                                    session.auth = (consumer_key, consumer_secret)
                                    product_id = ele.get('id')
                                    endpoint = f"{url}/products/{product_id}/variations"
                                    response = session.get(endpoint)
                                    if response.status_code == 200:
                                        parsed_variants_data = json.loads(response.text)
                                        product_variant = self.env['product.product'].sudo().search(
                                            [('product_tmpl_id', '=', product.id)])

                                        lines_without_no_variants = product.valid_product_template_attribute_line_ids._without_no_variant_attributes()
                                        all_variants = product.with_context(active_test=False).product_variant_ids.sorted(
                                            lambda p: (p.active, -p.id))
                                        single_value_lines = lines_without_no_variants.filtered(
                                            lambda ptal: len(ptal.product_template_value_ids._only_active()) == 1)
                                        if single_value_lines:
                                            for variant in all_variants:
                                                combination = variant.product_template_attribute_value_ids | single_value_lines.product_template_value_ids._only_active()

                                        all_combinations = itertools.product(*[
                                            ptal.product_template_value_ids._only_active() for ptal in
                                            lines_without_no_variants
                                        ])

                                        if parsed_variants_data:
                                            for variant in parsed_variants_data:
                                                list_1 = []
                                                for var in variant.get('attributes'):
                                                    list_1.append(var.get('option'))
                                                for item in product_variant:
                                                    if item.product_template_attribute_value_ids:
                                                        list_values = []
                                                        for rec in item.product_template_attribute_value_ids:
                                                            if list_1 and rec.name == list_1[0]:
                                                                if item.lst_price != item.woo_sale_price:
                                                                    if variant.get('sale_price'):
                                                                        price_extra = item.lst_price - float(
                                                                            variant.get('sale_price'))
                                                                    elif variant.get('regular_price'):
                                                                        price_extra = item.lst_price - float(
                                                                            variant.get('regular_price'))
                                                                    else:
                                                                        price_extra = 0
                                                                    # price_extra = item.lst_price - float(variant.get('sale_price')) if variant.get('sale_price') else item.lst_price - float(variant.get('regular_price'))
                                                                    if price_extra >= 0:
                                                                        rec.price_extra = price_extra
                                                                    else:
                                                                        rec.price_extra = -(price_extra)
                                                            list_values.append(rec.name)

                                                        if set(list_1).issubset(list_values):
                                                            item.default_code = variant.get('sku')
                                                            item.woo_sale_price = variant.get('sale_price') if variant.get('sale_price') else variant.get('regular_price')
                                                            item.woo_regular_price = variant.get('regular_price')
                                                            item.woo_id = variant.get('id')
                                                            item.woo_instance_id = instance_id
                                                            item.qty_available = variant.get('stock_quantity')
                                                            item.woo_product_weight = variant.get('weight')
                                                            item.weight = variant.get('weight')
                                                            item.is_exported = True
                                                            if variant.get('dimensions'):
                                                                if variant.get('dimensions').get('length'):
                                                                    item.woo_product_length = variant.get('dimensions').get('length')
                                                                if variant.get('dimensions').get('width'):
                                                                    item.woo_product_width = variant.get('dimensions').get('width')
                                                                if variant.get('dimensions').get('height'):
                                                                    item.woo_product_height = variant.get('dimensions').get('height')
                                                                item.volume = item.woo_product_length * item.woo_product_width * item.woo_product_height
                                                            if variant.get('description'):
                                                                item.woo_varient_description = variant.get('description').replace('<p>', '').replace('</p>', '')
                                                                item.description = variant.get('description')
                                                                # item.description_sale = variant.get(
                                                                #     'description').replace('<p>', '').replace('</p>',
                                                                #                                               '')
                                                                item.description_sale = item.name
                                                            else:
                                                                item.description = item.name
                                            for combination_tuple in all_combinations:
                                                combination = self.env['product.template.attribute.value'].concat(
                                                    *combination_tuple)
                                                list_var = []
                                                for n in combination:
                                                    list_var.append(n.name)

                                product.default_code = ele.get('sku')

                                for rec in ele.get('meta_data'):
                                    if rec.get('key') == '_wcfm_product_author':
                                        vendor_id = rec.get('value')
                                        vendor_odoo_id = self.env['res.partner'].sudo().search([('woo_id', '=', vendor_id)],
                                                                                        limit=1)
                                        if vendor_odoo_id:
                                            vendor_supplier_info = self.env['product.supplierinfo'].sudo().search(
                                                [('name', '=', vendor_odoo_id.id), ('product_id', '=', product.id)],
                                                limit=1)
                                            if not vendor_supplier_info:
                                                seller = self.env['product.supplierinfo'].sudo().create({
                                                    'name': vendor_odoo_id.id,
                                                    'product_id': product.id
                                                })
                                                product.seller_ids = [(6, 0, [seller.id])]

                                    if rec.get('key') == '_wcfmmp_commission':
                                        product.commission_type = rec.get('value').get('commission_mode')
                                        if product.commission_type == 'percent':
                                            product.commission_value = rec.get('value').get('commission_percent')
                                        elif product.commission_type == 'fixed':
                                            product.fixed_commission_value = rec.get('value').get('commission_fixed')
                                        elif product.commission_type == 'percent_fixed':
                                            product.commission_value = rec.get('value').get('commission_percent')
                                            product.fixed_commission_value = rec.get('value').get('commission_fixed')
                                self.env.cr.commit()
                else:
                    page = 0
            else:
                page = 0

    def import_inventory(self, instance_id):
        page = 1
        while page > 0 :
            location = instance_id.url
            cons_key = instance_id.client_id
            sec_key = instance_id.client_secret
            version = 'wc/v3'

            wcapi = API(url=location,
                        consumer_key=cons_key,
                        consumer_secret=sec_key,
                        version=version,
                        timeout=900
                        )
            url = "products"
            try:
                data = wcapi.get(url, params={'orderby': 'id', 'order': 'asc', 'per_page': 100, 'page': page})
                page += 1

            except Exception as error:
                raise UserError(_("Please check your connection and try again"))

            if data.status_code == 200 and data.content:
                parsed_data = data.json()
                if len(parsed_data) == 0:
                    page = 0
                if parsed_data:
                    for ele in parsed_data:
                        # For products with variants in odoo
                        product = self.env['product.product'].sudo().search(
                            ['|', ('woo_id', '=', ele.get('id')), ('default_code', '=', ele.get('sku'))], limit=1)
                        if product:
                            if ele.get('stock_quantity') and ele.get('stock_quantity') > 0:
                                res_product_qty = self.env['stock.change.product.qty'].sudo().search([('product_id', '=', product.id)], limit=1)
                                dict_q = {}
                                dict_q['new_quantity'] = ele.get('stock_quantity')
                                dict_q['product_id'] = product.id
                                dict_q['product_tmpl_id'] = product.product_tmpl_id.id

                                if not res_product_qty:
                                    create_qty = self.env['stock.change.product.qty'].sudo().create(dict_q)
                                    create_qty.change_product_qty()
                                else:
                                    write_qty = res_product_qty.sudo().write(dict_q)
                                    qty_id = self.env['stock.change.product.qty'].sudo().search(
                                        [('product_id', '=', product.id)],
                                        limit=1)
                                    if qty_id:
                                        qty_id.change_product_qty()

                        # For products without variants
                        product = self.env['product.template'].sudo().search(
                            ['|', ('woo_id', '=', ele.get('id')), ('default_code', '=', ele.get('sku'))], limit=1)
                        if product:
                            url = location + 'wp-json/wc/v3'
                            consumer_key = cons_key
                            consumer_secret = sec_key
                            session = requests.Session()
                            session.auth = (consumer_key, consumer_secret)
                            product_id = product.woo_id
                            endpoint = f"{url}/products/{product_id}/variations"
                            response = session.get(endpoint)
                            if response.status_code == 200:
                                parsed_variants_data = json.loads(response.text)
                                for ele in parsed_variants_data:
                                    if ele.get('stock_quantity') and ele.get('stock_quantity') > 0:
                                        product_p = self.env['product.product'].sudo().search(
                                            ['|', ('woo_id', '=', ele.get('id')), ('default_code', '=', ele.get('sku'))],
                                            limit=1)
                                        if product_p:
                                            res_product_qty = self.env['stock.change.product.qty'].sudo().search(
                                                [('product_id', '=', product_p.id)],
                                                limit=1)
                                            dict_q = {}
                                            dict_q['new_quantity'] = ele.get('stock_quantity')
                                            dict_q['product_id'] = product_p.id
                                            dict_q['product_tmpl_id'] = product_p.product_tmpl_id.id

                                            if not res_product_qty:
                                                create_qty = self.env['stock.change.product.qty'].sudo().create(dict_q)
                                                create_qty.change_product_qty()
                                            else:
                                                write_qty = res_product_qty.sudo().write(dict_q)
                                                qty_id = self.env['stock.change.product.qty'].sudo().search(
                                                    [('product_id', '=', product_p.id)],
                                                    limit=1)
                                                if qty_id:
                                                    qty_id.change_product_qty()

                            product.woo_product_qty = ele.get('stock_quantity') if ele.get('stock_quantity') and ele.get('stock_quantity') > 0 else 0.00
            else:
                page = 0


    def woo_import_product(self, product_data):
        instance_ids = self.env['woo.instance'].sudo().search([], limit=1)
        for instance_id in instance_ids:
            ele = product_data
            location = instance_id.url
            cons_key = instance_id.client_id
            sec_key = instance_id.client_secret
            version = 'wc/v3'
            product_record = self.env['product.template'].sudo().search(
                [('woo_id', '=', ele.get('id'))], limit=1)
            if not product_record:
                pro_t = []
                categ_list = []
                public_categ_list = []
                if ele.get('sku'):
                    product = self.env['product.template'].sudo().search(
                        ['|', ('woo_id', '=', ele.get('id')), ('default_code', '=', ele.get('sku'))], limit=1)
                else:
                    product = self.env['product.template'].sudo().search([('woo_id', '=', ele.get('id'))], limit=1)

                ''' This is used to update woo_id of a product, this
                will avoid duplication of product while syncing product.
                '''
                product_without_woo_id = self.env['product.template'].sudo().search(
                    [('woo_id', '=', False), ('default_code', '=', ele.get('sku'))], limit=1)

                product_product_without_id = self.env['product.product'].sudo().search(
                    [('product_tmpl_id', '=', product_without_woo_id.id)], limit=1)

                dict_p = {}
                dict_p['is_exported'] = True
                # dict_p['woo_instance_id'] = instance_id.id
                dict_p['company_id'] = instance_id.woo_company_id.id
                dict_p['woo_instance_ids'] = [(4, instance_id.id)]
                dict_p['woo_id'] = ele.get('id') if ele.get('id') else ''
                dict_p['website_published'] = True if ele.get('status') and ele.get('status') == 'publish' else False
                dict_p['name'] = ele.get('name') if ele.get('name') else ''
                if ele.get('description'):
                    parsed_desc = ele.get('description').replace('<h1>', '<h6>').replace('</h1>', '</h6>')
                    parsed_desc = parsed_desc.replace('<h2>', '<h6>').replace('</h2>', '</h6>')
                    parsed_desc = parsed_desc.replace('<h3>', '<h6>').replace('</h3>', '</h6>')
                    dict_p['description'] = parsed_desc
                    soup = BeautifulSoup(ele.get('description'), 'html.parser')
                    description_converted_to_text = soup.get_text()
                    # dict_p['description_sale'] = description_converted_to_text
                    dict_p['description_sale'] = ele.get('sku') + " " + ele.get('name')
                dict_p['woo_short_description'] = ele.get('short_description') if ele.get('short_description') else ''
                dict_p['default_code'] = ele.get('sku') if ele.get('sku') else ''

                for rec in ele.get('categories'):
                    categ = self.env['product.category'].sudo().search([('woo_id', '=', rec.get('id'))], limit=1)
                    if categ and categ.id not in categ_list:
                        categ_list.append(categ.id)

                    categ = self.env['product.public.category'].sudo().search(
                        [('woo_id', '=', rec.get('id'))],
                        limit=1)
                    if categ and categ.id not in public_categ_list:
                        public_categ_list.append(categ.id)

                if ele.get('categories') and ele.get('categories')[0].get('name'):
                    categ = self.env['product.category'].sudo().search(
                        [('name', '=', ele.get('categories')[0].get('name'))], limit=1)
                    if categ:
                        dict_p['categ_id'] = categ[0].id

                dict_p['list_price'] = ele.get('price') if ele.get('price') else 0.0
                dict_p['woo_sale_price'] = ele.get('price') if ele.get('price') else 0.0
                dict_p['woo_regular_price'] = ele.get('regular_price') if ele.get('regular_price') else 0.0
                dict_p['purchase_ok'] = True  # if ele.get('purchaseable') and ele.get('purchaseable') == True else True
                dict_p['sale_ok'] = True  # if ele.get('on_sale') and ele.get('on_sale') == True else False
                dict_p['qty_available'] = True if ele.get('stock_quantity') else 0.00

                if ele.get('images'):
                    url = ele.get('images')[0].get('src')
                    response = requests.get(url)
                    if response.status_code == 200:
                        if imghdr.what(None, response.content) != 'webp':
                            image = base64.b64encode(requests.get(url).content)
                            dict_p['image_1920'] = image

                dict_p['weight'] = float(ele.get('weight')) if ele.get('weight') else 0.00
                dict_p['woo_product_weight'] = float(ele.get('weight')) if ele.get('weight') else 0.00
                dict_p['woo_product_length'] = float(ele.get('dimensions').get('length')) if ele.get(
                    'dimensions') and ele.get('dimensions').get('length') else 0.00
                dict_p['woo_product_width'] = float(ele.get('dimensions').get('width')) if ele.get(
                    'dimensions') and ele.get('dimensions').get('width') else 0.00
                dict_p['woo_product_height'] = float(ele.get('dimensions').get('height')) if ele.get(
                    'dimensions') and ele.get('dimensions').get('height') else 0.00

                if ele.get('tags'):
                    for rec in ele.get('tags'):
                        existing_tag = self.env['product.tag'].sudo().search(
                            ['|', ('woo_id', '=', rec.get('id')), ('name', '=', rec.get('name'))], limit=1)
                        dict_value = {}
                        dict_value['is_exported'] = True
                        dict_value['woo_instance_id'] = instance_id.id
                        dict_value['name'] = rec.get('name') if rec.get('name') else ''
                        dict_value['woo_id'] = rec.get('id') if rec.get('id') else ''
                        dict_value['description'] = rec.get('description') if rec.get('description') else ''
                        dict_value['slug'] = rec.get('slug') if rec.get('slug') else ''

                        if not existing_tag:
                            create_tag_value = self.env['product.tag'].sudo().create(dict_value)
                            pro_t.append(create_tag_value.id)
                        else:
                            write_tag_value = existing_tag.sudo().write(dict_value)
                            pro_t.append(existing_tag.id)

                if not product or product_without_woo_id:
                    if not product_without_woo_id.woo_instance_id:
                        dict_p['woo_instance_id'] = instance_id.id
                    product_without_woo_id.sudo().write(dict_p)
                    if product_product_without_id and not ele.get('variations'):
                        product_product_without_id.sudo().write({
                            'is_exported': True,
                            'woo_id': dict_p['woo_id'],
                            'woo_sale_price': product_without_woo_id.woo_sale_price,
                            'default_code': ele.get('sku'),
                            'qty_available': dict_p['qty_available']
                        })

                if product and not product_without_woo_id:
                    if not product.woo_instance_id:
                        dict_p['woo_instance_id'] = instance_id.id
                    product.sudo().write(dict_p)

                if not product and not product_without_woo_id:
                    dict_p['type'] = 'product'
                    dict_p['woo_instance_id'] = instance_id.id
                    '''If product is not present we create it'''
                    pro_create = self.env['product.template'].sudo().create(dict_p)
                    product_product_vr = self.env['product.product'].sudo().search(
                        [('product_tmpl_id', '=', pro_create.id)], limit=1)
                    if product_product_vr and not ele.get('variations'):
                        product_product_vr.sudo().write({
                            'is_exported': True,
                            'woo_id': dict_p['woo_id'],
                            'woo_sale_price': pro_create.woo_sale_price,
                            'default_code': ele.get('sku'),
                            'qty_available': dict_p['qty_available']
                        })
                    if pro_t:
                        pro_create.product_tag_ids = [(4, val) for val in pro_t]
                    if categ_list:
                        pro_create.product_category_ids = [(4, val) for val in categ_list]
                    if public_categ_list:
                        pro_create.public_categ_ids = [(4, val) for val in public_categ_list]

                    result = []
                    post_list = []
                    if pro_create:
                        for rec in ele.get('meta_data'):
                            if rec.get('key').startswith('article_mapping_'):
                                if rec.get('value'):
                                    result.append(int(rec.get('value')))
                                    if result:
                                        for res in result:
                                            blog_post = self.env['blog.post'].sudo().search([('woo_id', '=', res)],
                                                                                            limit=1)
                                            if blog_post and blog_post.id not in post_list:
                                                post_list.append(blog_post.id)
                                                blog_post.product_template_ids = [(4, pro_create.id)]
                            if rec.get('key') == '_wcfm_product_author':
                                vendor_id = rec.get('value')
                                vendor_odoo_id = self.env['res.partner'].sudo().search([('woo_id', '=', vendor_id)],
                                                                                       limit=1)
                                if vendor_odoo_id:
                                    seller = self.env['product.supplierinfo'].sudo().create({
                                        'name': vendor_odoo_id.id,
                                        'product_id': pro_create.id
                                    })
                                    pro_create.seller_ids = [(6, 0, [seller.id])]

                            if rec.get('key') == '_wcfmmp_commission':
                                pro_create.commission_type = rec.get('value').get('commission_mode')
                                if pro_create.commission_type == 'percent':
                                    pro_create.commission_value = rec.get('value').get('commission_percent')
                                elif pro_create.commission_type == 'fixed':
                                    pro_create.fixed_commission_value = rec.get('value').get('commission_fixed')
                                elif pro_create.commission_type == 'percent_fixed':
                                    pro_create.commission_value = rec.get('value').get('commission_percent')
                                    pro_create.fixed_commission_value = rec.get('value').get('commission_fixed')

                            if rec.get('key') == 'additional_description':
                                additional_desc1 = rec.get('value').replace('<h1>', '<h6>').replace('</h1>', '</h6>')
                                additional_desc1 = re.sub('(<strong>)', '<br>\\1', additional_desc1)
                                additional_desc1 = re.sub(
                                    r'\[caption[^]]*]<img([^>]*)>(.*?)\[/caption]',
                                    r'<div style="text-align: left;"><div style="display: inline-block;"><img\1><br></div><div style="display: inline-block; width: calc(100% - 250px);">\2</div></div>',
                                    additional_desc1,
                                    flags=re.DOTALL
                                )
                                additional_desc1 = re.sub(r'(?<!\S)\n(?!\S)', '<br>', additional_desc1)
                                additional_desc1 = additional_desc1.replace('<h2>', '<h6>').replace('</h2>', '</h6>')
                                additional_desc1 = additional_desc1.replace('<h3>', '<h6>').replace('</h3>', '</h6>')
                                pro_create.woo_details = additional_desc1
                            if rec.get('key') == 'additional_description2':
                                additional_desc2 = rec.get('value').replace('<h1>', '<h6>').replace('</h1>', '</h6>')
                                additional_desc2 = re.sub('(<strong>)', '<br>\\1', additional_desc2)
                                additional_desc2 = re.sub(
                                    r'\[caption[^]]*]<img([^>]*)>(.*?)\[/caption]',
                                    r'<div style="text-align: left;"><div style="display: inline-block;"><img\1><br></div><div style="display: inline-block; width: calc(100% - 250px);">\2</div></div>',
                                    additional_desc2,
                                    flags=re.DOTALL
                                )
                                additional_desc2 = re.sub(r'(?<!\S)\n(?!\S)', '<br>', additional_desc2)
                                additional_desc2 = additional_desc2.replace('<h2>', '<h6>').replace('</h2>', '</h6>')
                                additional_desc2 = additional_desc2.replace('<h3>', '<h6>').replace('</h3>', '</h6>')
                                pro_create.woo_ingredients = additional_desc2
                            if rec.get('key') == 'additional_description3':
                                additional_desc3 = rec.get('value').replace('<h1>', '<h6>').replace('</h1>', '</h6>')
                                additional_desc3 = re.sub('(<strong>)', '<br>\\1', additional_desc3)
                                additional_desc3 = re.sub(
                                    r'\[caption[^]]*]<img([^>]*)>(.*?)\[/caption]',
                                    r'<div style="text-align: left;"><div style="display: inline-block;"><img\1><br></div><div style="display: inline-block; width: calc(100% - 250px);">\2</div></div>',
                                    additional_desc3,
                                    flags=re.DOTALL
                                )
                                additional_desc3 = re.sub(r'(?<!\S)\n(?!\S)', '<br>', additional_desc3)
                                additional_desc3 = additional_desc3.replace('<h2>', '<h6>').replace('</h2>', '</h6>')
                                additional_desc3 = additional_desc3.replace('<h3>', '<h6>').replace('</h3>', '</h6>')
                                pro_create.woo_instructions = additional_desc3
                            if rec.get('key') == 'additional_description4':
                                additional_desc4 = rec.get('value').replace('<h1>', '<h6>').replace('</h1>', '</h6>')
                                additional_desc4 = re.sub('(<strong>)', '<br>\\1', additional_desc4)
                                additional_desc4 = re.sub(
                                    r'\[caption[^]]*]<img([^>]*)>(.*?)\[/caption]',
                                    r'<div style="text-align: left;"><div style="display: inline-block;"><img\1><br></div><div style="display: inline-block; width: calc(100% - 250px);">\2</div></div>',
                                    additional_desc4,
                                    flags=re.DOTALL
                                )
                                additional_desc4 = re.sub(r'(?<!\S)\n(?!\S)', '<br>', additional_desc4)
                                additional_desc4 = additional_desc4.replace('<h2>', '<h6>').replace('</h2>', '</h6>')
                                additional_desc4 = additional_desc4.replace('<h3>', '<h6>').replace('</h3>', '</h6>')
                                pro_create.woo_scientific_ref = additional_desc4
                            if rec.get('key') == 'product_videos':
                                pro_create.woo_product_videos = rec.get('value')

                        if post_list:
                            pro_create.blog_post_ids = [(4, val) for val in post_list]

                        if ele.get('attributes'):
                            dict_attr = {}
                            for rec in ele.get('attributes'):
                                product_attr = self.env['product.attribute'].sudo().search(
                                    ['|', ('woo_id', '=', rec.get('id')), ('name', '=', rec.get('name'))], limit=1)
                                dict_attr['is_exported'] = True
                                dict_attr['woo_instance_id'] = instance_id.id
                                dict_attr['woo_id'] = rec.get('id') if rec.get('id') else ''
                                dict_attr['name'] = rec.get('name') if rec.get('name') else ''
                                dict_attr['slug'] = rec.get('slug') if rec.get('slug') else ''

                                pro_val = []
                                if rec.get('options'):
                                    for value in rec.get('options'):
                                        existing_attr_value = self.env['product.attribute.value'].sudo().search(
                                            [('name', '=', value), ('attribute_id', '=', product_attr.id)], limit=1)
                                        dict_value = {}
                                        dict_value['is_exported'] = True
                                        dict_value['woo_instance_id'] = instance_id.id
                                        dict_value['name'] = value if value else ''
                                        dict_value['attribute_id'] = product_attr.id

                                        if not existing_attr_value and dict_value['attribute_id']:
                                            create_value = self.env['product.attribute.value'].sudo().create(dict_value)
                                            pro_val.append(create_value.id)
                                        elif existing_attr_value:
                                            write_value = existing_attr_value.sudo().write(dict_value)
                                            pro_val.append(existing_attr_value.id)

                                if product_attr:
                                    if pro_val:
                                        exist = self.env['product.template.attribute.line'].sudo().search(
                                            [('attribute_id', '=', product_attr.id),
                                             ('value_ids', 'in', pro_val),
                                             ('product_tmpl_id', '=', pro_create.id)], limit=1)
                                        if not exist:
                                            exist = self.env['product.template.attribute.line'].sudo().create({
                                                'attribute_id': product_attr.id,
                                                'value_ids': [(6, 0, pro_val)],
                                                'product_tmpl_id': pro_create.id
                                            })
                                        else:
                                            exist.sudo().write({
                                                'attribute_id': product_attr.id,
                                                'value_ids': [(6, 0, pro_val)],
                                                'product_tmpl_id': pro_create.id
                                            })

                        if ele.get('variations'):
                            url = location + 'wp-json/wc/v3'
                            consumer_key = cons_key
                            consumer_secret = sec_key
                            session = requests.Session()
                            session.auth = (consumer_key, consumer_secret)
                            product_id = ele.get('id')
                            endpoint = f"{url}/products/{product_id}/variations"
                            response = session.get(endpoint)
                            if response.status_code == 200 and response.text:
                                parsed_variants_data = json.loads(response.text)
                                variant_list = []
                                product_variant = self.env['product.product'].sudo().search(
                                    [('product_tmpl_id', '=', pro_create.id)])
                                lines_without_no_variants = pro_create.valid_product_template_attribute_line_ids._without_no_variant_attributes()
                                all_variants = pro_create.with_context(active_test=False).product_variant_ids.sorted(
                                    lambda p: (p.active, -p.id))
                                single_value_lines = lines_without_no_variants.filtered(
                                    lambda ptal: len(ptal.product_template_value_ids._only_active()) == 1)
                                if single_value_lines:
                                    for variant in all_variants:
                                        combination = variant.product_template_attribute_value_ids | single_value_lines.product_template_value_ids._only_active()
                                all_combinations = itertools.product(*[
                                    ptal.product_template_value_ids._only_active() for ptal in lines_without_no_variants
                                ])

                                if parsed_variants_data:
                                    for variant in parsed_variants_data:
                                        list_1 = []
                                        for var in variant.get('attributes'):
                                            list_1.append(var.get('option'))
                                        for item in product_variant:
                                            if item.product_template_attribute_value_ids:
                                                list_values = []
                                                for rec in item.product_template_attribute_value_ids:
                                                    if list_1 and rec.name == list_1[0]:
                                                        if variant.get('sale_price'):
                                                            price_extra = item.lst_price - float(
                                                                variant.get('sale_price'))
                                                        elif variant.get('regular_price'):
                                                            price_extra = item.lst_price - float(
                                                                variant.get('regular_price'))
                                                        else:
                                                            price_extra = 0

                                                        if price_extra >= 0:
                                                            rec.price_extra = price_extra
                                                        else:
                                                            rec.price_extra = -(price_extra)
                                                    list_values.append(rec.name)
                                                if set(list_1).issubset(list_values):
                                                    item.default_code = variant.get('sku')
                                                    item.woo_sale_price = variant.get('sale_price') if variant.get(
                                                        'sale_price') else variant.get('regular_price')
                                                    item.woo_regular_price = variant.get('regular_price')
                                                    item.woo_id = variant.get('id')
                                                    item.woo_instance_id = instance_id
                                                    item.qty_available = variant.get('stock_quantity')
                                                    item.woo_product_weight = variant.get('weight')
                                                    item.weight = variant.get('weight')
                                                    item.is_exported = True
                                                    if variant.get('dimensions'):
                                                        if variant.get('dimensions').get('length'):
                                                            item.woo_product_length = variant.get('dimensions').get(
                                                                'length')
                                                        if variant.get('dimensions').get('width'):
                                                            item.woo_product_width = variant.get('dimensions').get(
                                                                'width')
                                                        if variant.get('dimensions').get('height'):
                                                            item.woo_product_height = variant.get('dimensions').get(
                                                                'height')
                                                    if variant.get('description'):
                                                        item.woo_varient_description = variant.get(
                                                            'description').replace('<p>', '').replace('</p>',
                                                                                                      '')
                                                        item.description = variant.get('description')
                                                        # item.description_sale = variant.get('description').replace(
                                                        #     '<p>', '').replace('</p>', '')
                                                        item.description_sale = item.name
                                                    # else:
                                                    #     item.description = item.name
                                    for combination_tuple in all_combinations:
                                        combination = self.env['product.template.attribute.value'].concat(
                                            *combination_tuple)
                                        list_var = []
                                        for n in combination:
                                            list_var.append(n.name)

                        pro_create.default_code = ele.get('sku')

                    self.env.cr.commit()
                else:
                    _logger.info('Product Exists')
