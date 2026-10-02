import base64
import logging

import requests

from odoo import models, fields
from odoo.exceptions import ValidationError

_logger = logging.getLogger("===+++ eCOm Product Template +++===")


class EgProductTemplate(models.Model):
    _inherit = 'eg.product.template'

    no_export_woo = fields.Boolean(string='No Export WC')
    is_woocommerce_tmpl_product = fields.Boolean(string='Available in WC')
    product_price = fields.Float(string='Product Price')

    regular_price = fields.Float(string='Regular Price')
    sale_ok = fields.Boolean(string="Product Sold")
    purchase_ok = fields.Boolean("Can be Purchased")

    date_on_sale_from = fields.Char(string="Sale start date")
    date_on_sale_to = fields.Char(string="Sale end date")

    slug = fields.Char(string="Slug")
    permalink = fields.Char(string='Permalink')
    woo_product_tmpl_type = fields.Selection(
        [('simple', 'Simple'), ('grouped', 'Grouped'), ('external', 'External'), ('variable', 'Variable')],
        string="Product Type")
    status = fields.Selection(
        [("draft", "Draft"), ("pending", "Pending"), ("private", "Private"), ("publish", "Publish"),
         ("importing", "Importing")])
    catalog_visibility = fields.Selection(
        [("visible", "Visible"), ("catalog", "Catalog"), ("search", "Search"), ("hidden", "Hidden")])
    virtual = fields.Boolean(string='Virtual')
    external_url = fields.Char(string='External Url')
    button_text = fields.Char(string='Button Text')
    tax_status = fields.Selection([('taxable', 'Taxable'), ('shipping', 'Shipping'), ('none', 'None')])
    tax_class = fields.Char(string='Tax Class')

    manage_stock = fields.Boolean(string='Manage Stock')
    stock_status = fields.Selection(
        [("instock", "Instock"), ("outofstock", "Outofstock"), ("onbackorder", "Onbackorder")])

    backorders = fields.Selection([("no", "No"), ("notify", "Notify"), ("yes", "Yes")])
    backorders_allowed = fields.Boolean(string='BackOrder Allowed')
    backordered = fields.Boolean(string='Backordered')
    sold_individually = fields.Boolean(string='Sold Individually')

    shipping_required = fields.Boolean(string='Shipping Required')
    shipping_taxable = fields.Boolean(string='Shipping Taxable')
    shipping_class = fields.Char(string='Shipping Class')
    shipping_class_id = fields.Integer(string='Shipping class id')

    reviews_allowed = fields.Boolean(string='Reviews Allowed')
    average_rating = fields.Float(string='Average Rating')
    rating_count = fields.Integer(string='Rating Count')
    product_tmpl_length = fields.Float(string='Length')
    product_tmpl_width = fields.Float(string='Width')
    product_tmpl_height = fields.Float(string='Height')
    need_to_update = fields.Boolean(string='Need To Update')

    product_attribute_ids = fields.One2many(comodel_name='eg.product.attribute', inverse_name='eg_product_tmpl_id')

    woo_product_tmpl_image_src = fields.Char(string='Image Src')

    def export_update_product_middle_to_ecom(self):
        for rec in self:
            if rec.instance_id.provider == "eg_woocommerce":
                rec.export_update_product_template_middle_to_wc()
        return super(EgProductTemplate, self).export_update_product_middle_to_ecom()

    def export_update_stock_middle_to_ecom(self):
        for rec in self:
            if rec.instance_id.provider == "eg_woocommerce":
                rec.update_woo_product_tmpl_stock(from_action=True)
        return super(EgProductTemplate, self).export_update_stock_middle_to_ecom()

    def export_update_price_middle_to_ecom(self):
        for rec in self:
            if rec.instance_id.provider == "eg_woocommerce":
                rec.update_product_tmpl_price()
        return super(EgProductTemplate, self).export_update_price_middle_to_ecom()

    def export_product_odoo_to_ecom(self):
        for rec in self:
            if rec.instance_id.provider == "eg_woocommerce":
                rec.woo_odoo_product_template_export()
        return super(EgProductTemplate, self).export_product_odoo_to_ecom()

    def check_product_sku(self, woo_tmpl_dict):
        _logger.info("{} not set a Sku".format(woo_tmpl_dict.get('name')))

    def set_product_categories(self, woo_category_dict=None, woo_api=None, wcapi=None):
        """
        In this create odoo category and mapping category from woocommerce when import product.
        :param woo_category_dict: dict of product category data
        :param woo_api: Browseable object of instance
        :param wcapi: woocommerce library
        :return: list of mapping category id
        """
        woo_categ_id = self.env['eg.product.category'].search(
            [('instance_product_category_id', '=', woo_category_dict.get('id')), ('instance_id', '=', woo_api.id)])
        if not woo_categ_id:
            domain = []  # New Changes by akash start
            woo_parent_id = None
            woo_category_dict = wcapi.get("products/categories/{}".format(woo_category_dict.get('id'))).json()
            if woo_category_dict.get("parent"):
                woo_parent_id = self.env["eg.product.category"].search(
                    [('instance_product_category_id', '=', woo_category_dict.get("parent")),
                     ('instance_id', '=', woo_api.id)])
                if woo_parent_id:
                    domain.append(("parent_id", "=", woo_parent_id.odoo_category_id.id))
                else:
                    self.set_product_categories(woo_category_dict={"id": woo_category_dict.get("parent")},
                                                woo_api=woo_api,
                                                wcapi=wcapi)
                    woo_parent_id = self.env["eg.product.category"].search(
                        [('instance_product_category_id', '=', woo_category_dict.get("parent")),
                         ('instance_id', '=', woo_api.id)])
                    domain.append(("parent_id", "=", woo_parent_id.odoo_category_id.id))

            else:
                domain.append(("parent_id", "in", ["", None, False]))
            odoo_product_categ_id = self.env['product.category'].search(
                [('name', '=', woo_category_dict.get('name'))] + domain)

            if not odoo_product_categ_id:
                data = {'name': woo_category_dict.get("name"),
                        'product_count': woo_category_dict.get("count"), }
                if woo_parent_id:
                    data.update({"parent_id": woo_parent_id.odoo_category_id.id})
                odoo_product_categ_id = self.env['product.category'].create(data)

            woo_product_category_obj = self.env['eg.product.category']
            woo_categ_id = woo_product_category_obj.create({
                'instance_id': woo_api.id,
                'instance_product_category_id': woo_category_dict.get("id"),
                'name': woo_category_dict.get("name"),
                'slug': woo_category_dict.get("slug"),
                'description': woo_category_dict.get("description"),
                'display': woo_category_dict.get("display"),
                'menu_order': woo_category_dict.get("menu_order"),
                'count': woo_category_dict.get("count"),
                'parent_id': woo_category_dict.get("parent"),
                'odoo_category_id': odoo_product_categ_id.id,
                'real_parent_id': woo_parent_id and woo_parent_id.id or None, })
        return woo_categ_id

    def set_product_tmpl_image(self, instance_id):
        """
        In this set product image from WooCommerce to middle layer with his variant
        :param instance_id: Browseable object of instance
        :return: Nothing
        """
        woo_api = instance_id
        try:  # Changes by Akash
            wcapi = woo_api.get_wcapi_connection()
        except Exception as e:
            raise Warning("{}".format(e))
        page = 1
        while page > 0:
            response = wcapi.get('products', params={'per_page': 100, 'page': page})
            if response.status_code == 200:
                if not response.json():
                    break
                page += 1
                for woo_tmpl_dict in response.json():
                    eg_product_tmpl_id = self.search(
                        [('inst_product_tmpl_id', '=', str(woo_tmpl_dict.get('id'))), ('instance_id', '=', woo_api.id)])
                    if eg_product_tmpl_id:
                        woo_product_image_obj = self.env['eg.template.image']
                        product_image_encoded_list = []
                        for product_image_dict in woo_tmpl_dict.get('images'):
                            headers = {
                                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/39.0.2171.95 Safari/537.36'}

                            product_image_encoded = base64.b64encode(
                                requests.get(product_image_dict.get('src'), headers=headers).content)
                            product_image_encoded_list.append(product_image_encoded)

                        for product_image in product_image_encoded_list:
                            woo_product_image_obj.create([{
                                'eg_template_id': eg_product_tmpl_id.id,
                                'template_image': product_image,
                            }])
                        eg_product_ids = wcapi.get(
                            "products/{}/variations".format(eg_product_tmpl_id.inst_product_tmpl_id)).json()
                        for woo_product_dict in eg_product_ids:
                            headers = {
                                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/39.0.2171.95 Safari/537.36'}
                            eg_product_id = self.env['eg.product.product'].search(
                                [('inst_product_id', '=', str(woo_product_dict.get('id')))])
                            if woo_product_dict.get('image'):
                                product_image_encoded = base64.b64encode(
                                    requests.get(woo_product_dict.get('image')['src'], headers=headers).content)
                                eg_product_id.write({
                                    'product_image': product_image_encoded
                                })
            else:
                _logger.info("Woo Product Template - Import product image : {}".format(response.text))

    def set_product_tmpl_main_image(self, woo_tmpl_dict):
        """
        In this get binary data of product images
        :param woo_tmpl_dict: Dict of product template data
        :return: Binary data of product template image
        """
        product_image_encoded = None
        if woo_tmpl_dict.get('images'):
            headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/39.0.2171.95 Safari/537.36'}

            product_image_encoded = base64.b64encode(
                requests.get(woo_tmpl_dict.get('images')[0].get('src'), headers=headers).content)
        return product_image_encoded

    def set_product_variant_src(self, woo_product_dict):
        """
        In this get product variant image source
        :param woo_product_dict: Dict of product variant data
        :return: Image source
        """
        product_image_src = None
        if woo_product_dict.get('image'):
            product_image_src = woo_product_dict.get('image')['src']
        return product_image_src

    def set_product_tmpl_src(self, woo_tmpl_dict):
        """
        In this get product template images source.
        :param woo_tmpl_dict: Dict of product template data
        :return: Image source
        """
        product_image_src_list = []
        if woo_tmpl_dict.get('images'):
            for product_image_dict in woo_tmpl_dict.get('images'):
                product_image_src_list.append(product_image_dict.get('src'))
            return ",".join(product_image_src_list)
        else:
            return ""

    def import_product_template(self, instance_id, product_tmpl_dict=None, eg_product_id=None):
        """
         In this method create odoo product with category, attribute, attribute value, and set image to middle layer
          and create record of mapping product and if product is already mapped so check any new variant add so
          add variant in odoo and middle layer, if odoo product is available but not in mappping so compare attribute a
          nd value if sem so mapping product else not mapped.
        :param instance_id: Browseable object of instance
        :param product_tmpl_dict: Dict of product template data
        :param eg_product_id: id of woocommerce product
        :return: Nothing
        """
        status = "no"
        text = ""
        partial = False
        history_id_list = []
        woo_api = instance_id
        page = 1
        try:
            wcapi = woo_api.get_wcapi_connection()
        except Exception as e:
            raise Warning("{}".format(e))
        while page > 0:
            if product_tmpl_dict:
                response = wcapi.get("products/{}".format(product_tmpl_dict.get('product_id')))
                page = 0
            elif eg_product_id:
                response = wcapi.get("products/{}".format(eg_product_id))
                page = 0
            else:
                response = wcapi.get('products', params={'per_page': 100, 'page': page})
                page += 1
            if response.status_code == 200:
                if product_tmpl_dict:
                    product_list = [response.json()]
                elif eg_product_id:
                    product_list = [response.json()]
                else:
                    product_list = response.json()
                if not product_list:
                    page = 0
                for woo_tmpl_dict in product_list:  # Changes by Akash
                    status = "no"
                    history_product_id = None
                    if woo_tmpl_dict.get("status") != "trash":
                        eg_product_tmpl_id = self.search(
                            [('inst_product_tmpl_id', '=', str(woo_tmpl_dict.get('id'))),
                             ('instance_id', '=', woo_api.id)])
                        eg_category_ids = self.env["eg.product.category"]
                        if woo_tmpl_dict.get("categories"):
                            for woo_category_dict in woo_tmpl_dict.get("categories"):
                                eg_category_id = self.set_product_categories(woo_category_dict=woo_category_dict,
                                                                             woo_api=woo_api, wcapi=wcapi)
                                eg_category_ids += eg_category_id

                        if not eg_product_tmpl_id or eg_product_tmpl_id and not eg_product_tmpl_id.odoo_product_tmpl_id:
                            if woo_tmpl_dict.get('type') == 'variable':
                                if woo_tmpl_dict.get('variations'):
                                    odoo_product_tmpl_id = None
                                    odoo_product_id = None
                                    if woo_tmpl_dict.get('attributes'):

                                        self.create_product_attributes(woo_tmpl_dict, woo_api)
                                    else:
                                        _logger.info(
                                            "This product is not create and not mapped because tpee is variant but not available attribute : {}".format(
                                                woo_tmpl_dict.get("name")))
                                        continue
                                    if woo_tmpl_dict.get("sku"):
                                        odoo_product_tmpl_id = self.env["product.template"].search(
                                            [("default_code", "=", woo_tmpl_dict.get("sku"))])
                                    if not woo_tmpl_dict.get("sku") or not odoo_product_tmpl_id:
                                        product_response = wcapi.get(
                                            "products/{}/variations/{}".format(woo_tmpl_dict.get('id'),
                                                                               woo_tmpl_dict.get('variations')[
                                                                                   0])).json()
                                        odoo_product_id = self.env['product.product'].search(
                                            [('default_code', '=', product_response.get('sku'))])
                                    if not odoo_product_id and not odoo_product_tmpl_id:
                                        odoo_product_tmpl_id = self.env['product.template'].create({
                                            'name': woo_tmpl_dict.get("name"),
                                            'list_price': woo_tmpl_dict.get("sale_price"),
                                            'default_code': woo_tmpl_dict.get("sku"),
                                            'create_date': woo_tmpl_dict.get("date_created"),
                                            'standard_price': woo_tmpl_dict.get("regular_price"),
                                            'sale_ok': woo_tmpl_dict.get("on_sale"),
                                            'purchase_ok': woo_tmpl_dict.get("purchasable"),
                                            'write_date': woo_tmpl_dict.get("date_modified"),
                                            'weight': woo_tmpl_dict.get("weight"),
                                            'sales_count': woo_tmpl_dict.get("total_sales"),
                                            'description': woo_tmpl_dict.get("description"),
                                            'type': 'product',
                                            'attribute_line_ids': self.set_odoo_product_attribute(woo_tmpl_dict,
                                                                                                  woo_api),
                                        })
                                        if eg_category_ids:
                                            odoo_product_tmpl_id.write(
                                                {"categ_id": eg_category_ids[0].odoo_category_id.id})
                                        mapping_product = True
                                    else:  # Changes by Akash
                                        # if odoo product is available so check attribute and his value sam or not
                                        # if not sem so don't mapping product
                                        if not odoo_product_tmpl_id:
                                            odoo_product_tmpl_id = odoo_product_id.product_tmpl_id
                                        check_attribute_value = self.check_product_attribute_import(
                                            odoo_product_tmpl_id=odoo_product_tmpl_id, woo_tmpl_dict=woo_tmpl_dict)
                                        if not check_attribute_value:
                                            _logger.info({
                                                "This product is not mapped because attribute value are different: {}".format(
                                                    woo_tmpl_dict.get("name"))})
                                            partial = True
                                            text = "This product is not mapped because attribute value are different"
                                            history_product_id = odoo_product_tmpl_id
                                            mapping_product = False
                                        else:
                                            mapping_product = True

                                        #  Changes by Akash
                                    if not eg_product_tmpl_id and mapping_product:
                                        self.create([{
                                            'product_tmpl_image': self.set_product_tmpl_main_image(woo_tmpl_dict),
                                            'is_woocommerce_tmpl_product': True,
                                            'instance_id': woo_api.id,
                                            'name': woo_tmpl_dict.get("name"),
                                            'product_price': woo_tmpl_dict.get("price"),
                                            'default_code': woo_tmpl_dict.get("sku"),
                                            'inst_product_tmpl_id': str(woo_tmpl_dict.get("id")),
                                            'odoo_product_tmpl_id': odoo_product_tmpl_id.id,

                                            'date_on_sale_from': woo_tmpl_dict.get("date_on_sale_from"),
                                            'date_on_sale_to': woo_tmpl_dict.get("date_on_sale_to"),

                                            'regular_price': woo_tmpl_dict.get("regular_price"),
                                            'price': woo_tmpl_dict.get('sale_price'),

                                            'sale_ok': woo_tmpl_dict.get("on_sale"),
                                            'purchase_ok': woo_tmpl_dict.get("purchasable"),
                                            'sale_count': woo_tmpl_dict.get("total_sales"),
                                            'eg_category_ids': [(6, 0, eg_category_ids and eg_category_ids.ids or [])],

                                            'slug': woo_tmpl_dict.get("slug"),
                                            'permalink': woo_tmpl_dict.get("permalink"),
                                            'status': woo_tmpl_dict.get("status"),
                                            'catalog_visibility': woo_tmpl_dict.get("catalog_visibility"),
                                            'virtual': woo_tmpl_dict.get("virtual"),
                                            'external_url': woo_tmpl_dict.get("external_url"),
                                            'button_text': woo_tmpl_dict.get("button_text"),
                                            'tax_status': woo_tmpl_dict.get("tax_status"),
                                            'tax_class': woo_tmpl_dict.get("tax_class"),
                                            'manage_stock': woo_tmpl_dict.get("manage_stock"),
                                            'stock_status': woo_tmpl_dict.get('stock_status'),
                                            'qty_available': woo_tmpl_dict.get('stock_quantity'),
                                            'backorders': woo_tmpl_dict.get("backorders"),
                                            'backorders_allowed': woo_tmpl_dict.get("backorders_allowed"),
                                            'backordered': woo_tmpl_dict.get("backordered"),
                                            'sold_individually': woo_tmpl_dict.get("sold_individually"),
                                            'shipping_required': woo_tmpl_dict.get("shipping_required"),
                                            'shipping_taxable': woo_tmpl_dict.get("shipping_taxable"),
                                            'shipping_class': woo_tmpl_dict.get("shipping_class"),
                                            'shipping_class_id': woo_tmpl_dict.get("shipping_class_id"),
                                            'reviews_allowed': woo_tmpl_dict.get("reviews_allowed"),
                                            'average_rating': woo_tmpl_dict.get("average_rating"),
                                            'rating_count': woo_tmpl_dict.get("rating_count"),
                                            'woo_product_tmpl_type': woo_tmpl_dict.get("type"),

                                            'product_tmpl_length': woo_tmpl_dict.get("dimensions")['length'],
                                            'product_tmpl_height': woo_tmpl_dict.get("dimensions")['height'],
                                            'product_tmpl_width': woo_tmpl_dict.get("dimensions")['width'],
                                            'eg_attribute_line_ids': self.set_woo_product_attribute(woo_tmpl_dict,
                                                                                                    woo_api),
                                            'woo_product_tmpl_image_src': self.set_product_tmpl_src(woo_tmpl_dict),
                                        }])

                                        # create it's Variant
                                        woo_product_variants = wcapi.get(
                                            "products/{}/variations".format(woo_tmpl_dict.get("id"))).json()
                                        #  Changes by Akash
                                        self.create_product_variant_mapping_import(
                                            woo_product_variants=woo_product_variants, woo_api=woo_api,
                                            woo_tmpl_dict=woo_tmpl_dict, eg_category_ids=eg_category_ids)
                                        status = "yes"
                                        text = "This product successfully create and mapping"
                                        history_product_id = odoo_product_tmpl_id
                                    else:
                                        partial = True
                                else:
                                    partial = True
                                    text = "This product type is variations but do no have any variation : {}".format(
                                        woo_tmpl_dict.get("name"))

                            elif woo_tmpl_dict.get('type') == 'simple':
                                if not woo_tmpl_dict.get('sku'):
                                    _logger.info(
                                        "{} not a SKU so not created in odoo!!!".format(woo_tmpl_dict.get('name')))
                                    continue
                                odoo_product_tmpl_id = self.env['product.template'].search(
                                    [('default_code', '=', woo_tmpl_dict.get('sku'))])
                                if not odoo_product_tmpl_id:
                                    odoo_product_tmpl_id = self.env['product.template'].create({
                                        'name': woo_tmpl_dict.get("name"),
                                        'list_price': woo_tmpl_dict.get("sale_price"),
                                        'default_code': woo_tmpl_dict.get("sku"),
                                        'create_date': woo_tmpl_dict.get("date_created"),
                                        'standard_price': woo_tmpl_dict.get("regular_price"),
                                        'sale_ok': woo_tmpl_dict.get("on_sale"),
                                        'purchase_ok': woo_tmpl_dict.get("purchasable"),
                                        'write_date': woo_tmpl_dict.get("date_modified"),
                                        'weight': woo_tmpl_dict.get("weight"),
                                        'sales_count': woo_tmpl_dict.get("total_sales"),
                                        'description': woo_tmpl_dict.get("description"),
                                        'qty_available': woo_tmpl_dict.get("stock_quantity") and float(
                                            woo_tmpl_dict.get("stock_quantity")) or 0.0,
                                        'type': 'product',
                                    })
                                    if eg_category_ids:
                                        odoo_product_tmpl_id.write(
                                            {"categ_id": eg_category_ids[0].odoo_category_id.id, })

                                if not eg_product_tmpl_id:
                                    eg_product_tmpl_id = self.create([{
                                        'product_tmpl_image': self.set_product_tmpl_main_image(woo_tmpl_dict),
                                        'is_woocommerce_tmpl_product': True,
                                        'instance_id': woo_api.id,
                                        'name': woo_tmpl_dict.get("name"),
                                        'product_price': woo_tmpl_dict.get("price"),
                                        'default_code': woo_tmpl_dict.get("sku"),
                                        'inst_product_tmpl_id': str(woo_tmpl_dict.get("id")),
                                        'odoo_product_tmpl_id': odoo_product_tmpl_id.id,

                                        'date_on_sale_from': woo_tmpl_dict.get("date_on_sale_from"),
                                        'date_on_sale_to': woo_tmpl_dict.get("date_on_sale_to"),

                                        'regular_price': woo_tmpl_dict.get("regular_price"),
                                        'price': woo_tmpl_dict.get('sale_price'),

                                        'sale_ok': woo_tmpl_dict.get("on_sale"),
                                        'purchase_ok': woo_tmpl_dict.get("purchasable"),
                                        'sale_count': woo_tmpl_dict.get("total_sales"),

                                        'slug': woo_tmpl_dict.get("slug"),
                                        'permalink': woo_tmpl_dict.get("permalink"),
                                        'status': woo_tmpl_dict.get("status"),
                                        'catalog_visibility': woo_tmpl_dict.get("catalog_visibility"),
                                        'virtual': woo_tmpl_dict.get("virtual"),
                                        'external_url': woo_tmpl_dict.get("external_url"),
                                        'button_text': woo_tmpl_dict.get("button_text"),
                                        'tax_status': woo_tmpl_dict.get("tax_status"),
                                        'tax_class': woo_tmpl_dict.get("tax_class"),
                                        'manage_stock': woo_tmpl_dict.get("manage_stock"),
                                        'stock_status': woo_tmpl_dict.get('stock_status'),
                                        'qty_available': woo_tmpl_dict.get('stock_quantity'),
                                        'backorders': woo_tmpl_dict.get("backorders"),
                                        'backorders_allowed': woo_tmpl_dict.get("backorders_allowed"),
                                        'backordered': woo_tmpl_dict.get("backordered"),
                                        'sold_individually': woo_tmpl_dict.get("sold_individually"),
                                        'shipping_required': woo_tmpl_dict.get("shipping_required"),
                                        'shipping_taxable': woo_tmpl_dict.get("shipping_taxable"),
                                        'shipping_class': woo_tmpl_dict.get("shipping_class"),
                                        'shipping_class_id': woo_tmpl_dict.get("shipping_class_id"),
                                        'reviews_allowed': woo_tmpl_dict.get("reviews_allowed"),
                                        'average_rating': woo_tmpl_dict.get("average_rating"),
                                        'rating_count': woo_tmpl_dict.get("rating_count"),
                                        'woo_product_tmpl_type': woo_tmpl_dict.get("type"),

                                        'product_tmpl_length': woo_tmpl_dict.get("dimensions")['length'],
                                        'product_tmpl_height': woo_tmpl_dict.get("dimensions")['height'],
                                        'product_tmpl_width': woo_tmpl_dict.get("dimensions")['width'],
                                        'eg_category_ids': [(6, 0, eg_category_ids and eg_category_ids.ids or [])],
                                    }])

                                    product_product_obj = self.env['eg.product.product']
                                    product_product_obj.create({
                                        'is_woocommerce_product': True,
                                        'instance_id': woo_api.id,
                                        'name': woo_tmpl_dict.get("name"),
                                        'inst_product_id': str(woo_tmpl_dict.get("id")),
                                        'odoo_product_id': odoo_product_tmpl_id.product_variant_id.id,
                                        'description': woo_tmpl_dict.get("description"),
                                        'permalink': woo_tmpl_dict.get("permalink"),
                                        'default_code': woo_tmpl_dict.get("sku"),
                                        'product_regular_price': woo_tmpl_dict.get("regular_price"),
                                        'price': woo_tmpl_dict.get("price"),
                                        'on_sale': woo_tmpl_dict.get("on_sale"),
                                        'status': woo_tmpl_dict.get("status"),
                                        'purchasable': woo_tmpl_dict.get("purchasable"),
                                        'virtual': woo_tmpl_dict.get("virtual"),
                                        'date_on_sale_from': woo_tmpl_dict.get("date_on_sale_from"),
                                        'date_on_sale_to': woo_tmpl_dict.get("date_on_sale_to"),
                                        'tax_status': woo_tmpl_dict.get("tax_status"),
                                        'tax_class': woo_tmpl_dict.get("tax_class"),
                                        'manage_stock': woo_tmpl_dict.get("manage_stock"),
                                        'qty_available': woo_tmpl_dict.get("stock_quantity"),
                                        'eg_category_ids': [(6, 0, eg_category_ids and eg_category_ids.ids or [])],
                                        'stock_status': woo_tmpl_dict.get("stock_status"),
                                        'backorders': woo_tmpl_dict.get("backorders"),
                                        'backorders_allowed': woo_tmpl_dict.get("backorders_allowed"),
                                        'backordered': woo_tmpl_dict.get("backordered"),
                                        'weight': woo_tmpl_dict.get("weight"),
                                        'product_length': woo_tmpl_dict.get("dimensions")['length'],
                                        'product_width': woo_tmpl_dict.get("dimensions")['width'],
                                        'product_height': woo_tmpl_dict.get("dimensions")['height'],
                                        'shipping_class': woo_tmpl_dict.get("shipping_class"),
                                        'shipping_class_id': woo_tmpl_dict.get("shipping_class_id"),
                                        'menu_order': woo_tmpl_dict.get("menu_order"),
                                        'eg_tmpl_id': eg_product_tmpl_id.id,
                                    })
                                if odoo_product_tmpl_id:
                                    status = "yes"
                                    text = "This product successfully create and mapping"
                                    history_product_id = odoo_product_tmpl_id
                                else:
                                    partial = True
                        else:  # Changes by Akash
                            # check any new value are add so add in odoo but don't add new attribute
                            if woo_tmpl_dict.get('type') == 'variable':
                                if woo_tmpl_dict.get('attributes'):
                                    self.create_product_attributes(woo_tmpl_dict, woo_api)
                                check_new_variant = self.check_new_product_variant_import(woo_tmpl_dict=woo_tmpl_dict,
                                                                                          eg_product_tmpl_id=eg_product_tmpl_id,
                                                                                          woo_api=woo_api)
                                if check_new_variant:
                                    _logger.info(
                                        "New Variant is add this product : {}".format(woo_tmpl_dict.get("name")))
                                    woo_product_variants = wcapi.get(
                                        "products/{}/variations".format(woo_tmpl_dict.get("id"))).json()
                                    variant_mapping = self.create_product_variant_mapping_import(
                                        woo_product_variants=woo_product_variants, woo_api=woo_api,
                                        woo_tmpl_dict=woo_tmpl_dict)  # Add Pro Version eg_category_ids=eg_category_ids
                                    text = "This product is already mapped but new variant are added"
                                    status = "yes"
                                    history_product_id = eg_product_tmpl_id.odoo_product_tmpl_id
                                else:
                                    continue
                            else:
                                continue
                    else:
                        text = "This product deleted in woocommerce so don't mapped"
                    eg_history_id = self.env["eg.sync.history"].create({"error_message": text,
                                                                        "status": status,
                                                                        "process_on": "product",
                                                                        "process": "a",
                                                                        "instance_id": woo_api.id,
                                                                        "product_id": history_product_id and history_product_id.id or None,
                                                                        "child_id": True})
                    history_id_list.append(eg_history_id.id)

            else:
                text = "Not get a response of a Woocommerce"
            if partial:
                status = "partial"
                text = "Some product was created and some product is not create"
            if status == "yes" and not partial:
                text = "All product was successfully created and mapped"
            if not history_id_list:
                status = "yes"
                text = "All product was already mapped"
            self.env["eg.sync.history"].create({"error_message": text,
                                                "status": status,
                                                "process_on": "product",
                                                "process": "a",
                                                "instance_id": woo_api.id,
                                                "parent_id": True,
                                                "eg_history_ids": [(6, 0, history_id_list)]})

    def create_product_variant_mapping_import(self, woo_api=None, woo_product_variants=None,
                                              woo_tmpl_dict=None,
                                              eg_category_ids=None):
        """
         In this method create mapping product variant and write data in odoo product variant.
        :param woo_api: Browseable object of instance
        :param woo_product_variants: lis of dict for product variant data
        :param woo_tmpl_dict: dict of product template data
        :return: True
        """
        for woo_product_dict in woo_product_variants:
            if woo_product_dict.get('sku'):
                woo_product_product_obj = self.env['eg.product.product']
                woo_product_variant_id = self.env['eg.product.product'].search(
                    [('inst_product_id', '=', str(woo_product_dict.get('id'))),
                     ('instance_id', '=', woo_api.id)])
                eg_product_tmpl_id = self.env['eg.product.template'].search(
                    [('inst_product_tmpl_id', '=', str(woo_tmpl_dict.get('id'))),
                     ('instance_id', '=', woo_api.id)])

                if not woo_product_variant_id:
                    attribute_list = []
                    for attribute in woo_product_dict.get('attributes'):
                        eg_attribute_id = self.env['eg.product.attribute'].search(
                            [('inst_attribute_id', '=', str(attribute.get('id'))), ('instance_id', '=', woo_api.id)])
                        woo_attribute_terms = self.env['eg.attribute.value'].search(
                            [('name', '=', attribute.get('option')),
                             ('inst_attribute_id', "=", eg_attribute_id.id), ('instance_id', '=', woo_api.id)])
                        if woo_attribute_terms:
                            attribute_list.append(woo_attribute_terms.id)
                    woo_product_product_id = woo_product_product_obj.create({
                        'is_woocommerce_product': True,
                        'instance_id': woo_api.id,
                        'name': woo_tmpl_dict.get('name'),
                        'inst_product_id': str(woo_product_dict.get('id')),
                        'default_code': woo_product_dict.get('sku'),
                        'eg_tmpl_id': eg_product_tmpl_id.id,
                        'eg_value_ids': [(6, 0, attribute_list)],
                        'product_regular_price': woo_product_dict.get(
                            'regular_price') and float(
                            woo_product_dict.get('regular_price')) or 0.0,
                        'price': woo_product_dict.get('sale_price') and float(
                            woo_product_dict.get('sale_price')) or 0.0,
                        'on_sale': woo_product_dict.get('on_sale'),
                        'purchasable': woo_product_dict.get('purchasable'),
                        'tax_status': woo_product_dict.get('tax_status'),
                        'tax_class': woo_product_dict.get('tax_class'),
                        'manage_stock': woo_product_dict.get('manage_stock'),
                        'stock_status': woo_product_dict.get('stock_status'),
                        'eg_category_ids': [(6, 0, eg_category_ids and eg_category_ids.ids or [])],
                        'backorders': woo_product_dict.get('backorders'),
                        'backorders_allowed': woo_product_dict.get('backorders_allowed'),
                        'backordered': woo_product_dict.get('backordered'),
                        'shipping_class': woo_product_dict.get('shipping_class'),
                        'shipping_class_id': woo_product_dict.get('shipping_class_id'),
                        'weight': woo_product_dict.get('weight'),
                        'product_length': woo_product_dict.get('dimensions')['length'],
                        'product_width': woo_product_dict.get('dimensions')['width'],
                        'product_height': woo_product_dict.get('dimensions')['height'],
                        'woo_product_image_src': self.set_product_variant_src(woo_product_dict),
                    })

                    for odoo_product_id in eg_product_tmpl_id.odoo_product_tmpl_id.product_variant_ids:
                        if odoo_product_id.product_template_attribute_value_ids == woo_product_product_id.eg_value_ids.mapped(
                                'odoo_attribute_value_id'):
                            woo_product_product_id.write(
                                {'odoo_product_id': odoo_product_id.id})
                            #  New Change by Akash
                            odoo_product_id.write({
                                'list_price': woo_product_dict.get('sale_price'),
                                'default_code': woo_product_dict.get('sku'),
                                'standard_price': woo_product_dict.get('regular_price'),
                                'sale_ok': woo_product_dict.get("on_sale"),
                                'purchase_ok': woo_product_dict.get("purchasable"),
                                'weight': woo_product_dict.get("weight"),
                                'description': woo_product_dict.get("description"),
                            })
        return True

    def import_update_woo_product_template(self, instance_id):
        """
        In this method update product and his variant woocommerce to odoo product with category and update to
         middle layer.
        :param instance_id: Browseable object of instance
        :return: Don't return anything
        """
        woo_api = instance_id
        try:  # Changes by Akash
            wcapi = woo_api.get_wcapi_connection()
        except Exception as e:
            raise Warning("{}".format(e))
        page = 1
        while page > 0:  # all code changed by flow
            status = "no"
            text = ""
            partial = False
            history_id_list = []
            response = wcapi.get('products', params={'per_page': 100, 'page': page})
            if response.status_code == 200:
                if not response.json():
                    break
                page += 1
                for woo_tmpl_dict in response.json():
                    text = "no"
                    eg_product_tmpl_id = self.search(
                        [('inst_product_tmpl_id', '=', str(woo_tmpl_dict.get("id"))), ('instance_id', '=', woo_api.id)])
                    eg_category_ids = self.env["eg.product.category"]
                    if woo_tmpl_dict.get("categories"):
                        for woo_category_dict in woo_tmpl_dict.get("categories"):
                            eg_category_id = self.set_product_categories(woo_category_dict=woo_category_dict,
                                                                         woo_api=woo_api, wcapi=wcapi)
                            eg_category_ids += eg_category_id
                    if eg_product_tmpl_id:
                        odoo_product_tmpl_id = eg_product_tmpl_id.odoo_product_tmpl_id
                        odoo_product_tmpl_id.write({'name': woo_tmpl_dict.get("name"),
                                                    'list_price': woo_tmpl_dict.get("sale_price"),
                                                    'create_date': woo_tmpl_dict.get("date_created"),
                                                    'standard_price': woo_tmpl_dict.get("regular_price"),
                                                    'sale_ok': woo_tmpl_dict.get("on_sale"),
                                                    'purchase_ok': woo_tmpl_dict.get("purchasable"),
                                                    'write_date': woo_tmpl_dict.get("date_modified"),
                                                    'weight': woo_tmpl_dict.get("weight"),
                                                    'sales_count': woo_tmpl_dict.get("total_sales"),
                                                    'description': woo_tmpl_dict.get("description"),
                                                    'type': 'product',
                                                    'qty_available': woo_tmpl_dict.get("stock_quantity") and float(
                                                        woo_tmpl_dict.get("stock_quantity")) or 0.0,
                                                    })
                        if eg_category_ids:
                            odoo_product_tmpl_id.write(
                                {"categ_id": eg_category_ids[0].odoo_category_id.id, })
                        if eg_product_tmpl_id:
                            eg_product_tmpl_id.write({
                                'name': woo_tmpl_dict.get("name"),
                                'product_price': woo_tmpl_dict.get("price"),
                                'default_code': woo_tmpl_dict.get("sku"),
                                'inst_product_tmpl_id': str(woo_tmpl_dict.get("id")),
                                'regular_price': woo_tmpl_dict.get("regular_price"),
                                'price': woo_tmpl_dict.get('sale_price'),
                                'sale_ok': woo_tmpl_dict.get("on_sale"),
                                'purchase_ok': woo_tmpl_dict.get("purchasable"),
                                'sale_count': woo_tmpl_dict.get("total_sales"),
                                'description': woo_tmpl_dict.get("description"),
                                'slug': woo_tmpl_dict.get("slug"),
                                'status': woo_tmpl_dict.get("status"),
                                'tax_status': woo_tmpl_dict.get("tax_status"),
                                'tax_class': woo_tmpl_dict.get("tax_class"),
                                'manage_stock': woo_tmpl_dict.get("manage_stock"),
                                'stock_status': woo_tmpl_dict.get('stock_status'),
                                'qty_available': woo_tmpl_dict.get('stock_quantity'),
                                'backorders': woo_tmpl_dict.get("backorders"),
                                'backorders_allowed': woo_tmpl_dict.get("backorders_allowed"),
                                'backordered': woo_tmpl_dict.get("backordered"),
                                'sold_individually': woo_tmpl_dict.get("sold_individually"),
                                'shipping_required': woo_tmpl_dict.get("shipping_required"),
                                'shipping_taxable': woo_tmpl_dict.get("shipping_taxable"),
                                'woo_product_tmpl_type': woo_tmpl_dict.get("type"),
                                'eg_category_ids': [(6, 0, eg_category_ids and eg_category_ids.ids or [])],
                                'product_tmpl_length': woo_tmpl_dict.get("dimensions")['length'],
                                'product_tmpl_height': woo_tmpl_dict.get("dimensions")['height'],
                                'product_tmpl_width': woo_tmpl_dict.get("dimensions")['width'],
                            })

                        # Odoo product Template Write (product.template)
                        if woo_tmpl_dict.get('type') == 'variable':
                            # create it's Variant
                            woo_product_variants = wcapi.get(
                                "products/{}/variations".format(woo_tmpl_dict.get("id"))).json()
                            for woo_product_dict in woo_product_variants:
                                product_variant_id = self.env['eg.product.product'].search(
                                    [('inst_product_id', '=', str(woo_product_dict.get('id'))),
                                     ('instance_id', '=', woo_api.id)])
                                if product_variant_id:
                                    product_variant_id.write({
                                        'name': woo_tmpl_dict.get('name'),
                                        'default_code': woo_product_dict.get('sku'),
                                        'product_regular_price': woo_product_dict.get('regular_price') and float(
                                            woo_product_dict.get('regular_price')) or 0.0,
                                        'price': woo_product_dict.get('sale_price') and float(
                                            woo_product_dict.get('regular_price')) or 0.0,
                                        'on_sale': woo_product_dict.get('on_sale'),
                                        'purchasable': woo_product_dict.get('purchasable'),
                                        'tax_status': woo_product_dict.get('tax_status'),
                                        'tax_class': woo_product_dict.get('tax_class'),
                                        'manage_stock': woo_product_dict.get('manage_stock'),
                                        'stock_status': woo_product_dict.get('stock_status'),
                                        'backorders': woo_product_dict.get('backorders'),
                                        'eg_category_ids': [(6, 0, eg_category_ids and eg_category_ids.ids or [])],
                                        'backorders_allowed': woo_product_dict.get('backorders_allowed'),
                                        'backordered': woo_product_dict.get('backordered'),
                                        'weight': woo_product_dict.get('weight'),
                                        'product_length': woo_product_dict.get('dimensions')['length'],
                                        'product_width': woo_product_dict.get('dimensions')['width'],
                                        'product_height': woo_product_dict.get('dimensions')['height'],
                                    })

                                    product_variant_id.odoo_product_id.write({
                                        'list_price': woo_product_dict.get('sale_price'),
                                        'default_code': woo_product_dict.get('sku'),
                                        'standard_price': woo_product_dict.get('regular_price'),
                                        'sale_ok': woo_product_dict.get("on_sale"),
                                        'purchase_ok': woo_product_dict.get("purchasable"),
                                        'weight': woo_product_dict.get("weight"),
                                        'description': woo_product_dict.get("description")})

                        elif woo_tmpl_dict.get('type') == 'simple':
                            product_variant_id = eg_product_tmpl_id.eg_product_ids[0]
                            product_variant_id.write({
                                'name': woo_tmpl_dict.get('name'),
                                'default_code': woo_tmpl_dict.get('sku'),
                                'product_regular_price': woo_tmpl_dict.get('regular_price') and float(
                                    woo_tmpl_dict.get('regular_price')) or 0.0,
                                'price': woo_tmpl_dict.get('sale_price') and float(
                                    woo_tmpl_dict.get('regular_price')) or 0.0,
                                'on_sale': woo_tmpl_dict.get('on_sale'),
                                'purchasable': woo_tmpl_dict.get('purchasable'),
                                'tax_status': woo_tmpl_dict.get('tax_status'),
                                'tax_class': woo_tmpl_dict.get('tax_class'),
                                'manage_stock': woo_tmpl_dict.get('manage_stock'),
                                'eg_category_ids': [(6, 0, eg_category_ids and eg_category_ids.ids or [])],
                                'stock_status': woo_tmpl_dict.get('stock_status'),
                                'backorders': woo_tmpl_dict.get('backorders'),
                                'backorders_allowed': woo_tmpl_dict.get('backorders_allowed'),
                                'backordered': woo_tmpl_dict.get('backordered'),
                                'weight': woo_tmpl_dict.get('weight'),
                                'product_length': woo_tmpl_dict.get('dimensions')['length'],
                                'product_width': woo_tmpl_dict.get('dimensions')['width'],
                                'product_height': woo_tmpl_dict.get('dimensions')['height'],
                                'description':woo_tmpl_dict.get('description'),
                            })

                            product_variant_id.odoo_product_id.write({'list_price': woo_tmpl_dict.get(
                                'sale_price') and float(woo_tmpl_dict.get('sale_price')) or 0,
                                                                      'default_code': woo_tmpl_dict.get('sku'),
                                                                      'standard_price': woo_tmpl_dict.get(
                                                                          'regular_price') and float(woo_tmpl_dict.get(
                                                                          'regular_price')) or 0,
                                                                      'sale_ok': woo_tmpl_dict.get("on_sale"),
                                                                      'purchase_ok': woo_tmpl_dict.get("purchasable"),
                                                                      'weight': woo_tmpl_dict.get("weight") and float(
                                                                          woo_tmpl_dict.get("weight")) or 0,
                                                                      'description': woo_tmpl_dict.get("description")})
                        status = "yes"
                        text = "This product is successfully update"
                        eg_history_id = self.env["eg.sync.history"].create({"error_message": text,
                                                                            "status": status,
                                                                            "process_on": "product",
                                                                            "process": "c",
                                                                            "instance_id": woo_api.id,
                                                                            "product_id": eg_product_tmpl_id.odoo_product_tmpl_id.id,
                                                                            "child_id": True})
                        history_id_list.append(eg_history_id.id)
                if partial:
                    status = "partial"
                    text = "Some product was update and some product is not update"
                if status == "yes" and not partial:
                    text = "All product was successfully update."
                if not history_id_list:
                    status = "no"
                    text = "Any product is not update"
                self.env["eg.sync.history"].create({"error_message": text,
                                                    "status": status,
                                                    "process_on": "product",
                                                    "process": "c",
                                                    "instance_id": woo_api.id,
                                                    "parent_id": True,
                                                    "eg_history_ids": [(6, 0, history_id_list)]})
            else:
                raise ValidationError('{}'.format(response.text))

    def create_product_image_url(self):
        return 'web/content/?model=eg.product.template&download=true&field=product_tmpl_image&id=%s&filename=download.png' % (
            self.id),

    def woo_odoo_product_template_export(self, instance_id=None):
        """
        In this create product from middle layer to WooCommerce with mapping product, export category, export attribute value.
        :param instance_id: Browseable object of instance
        :return: Nothing
        """
        status = "no"
        text = ""
        partial = False
        history_id_list = []
        if self:
            eg_product_tmpl_ids = self
        else:
            eg_product_tmpl_ids = self.search([("instance_id", "=", instance_id.id)])
        for record in eg_product_tmpl_ids:
            woo_api = record.instance_id
            try:  # Changes by Akash
                wcapi = woo_api.get_wcapi_connection()
            except Exception as e:
                raise Warning("{}".format(e))
            if not record.is_woocommerce_tmpl_product:
                status = "no"
                eg_product_pricelist_id = self.env['eg.product.pricelist'].search(
                    [('id', '=', woo_api.eg_product_pricelist_id.id)])

                product_price = None
                if eg_product_pricelist_id:
                    for woo_product_pricelist_line in eg_product_pricelist_id.eg_product_pricelist_line_ids:
                        if record.id == woo_product_pricelist_line.eg_product_template_id.id:
                            product_price = woo_product_pricelist_line.price_unit
                            break
                        else:
                            product_price = record.price

                # if product attribute available of current product Template so export a product type of product variable
                attribute_lines = []
                if record.eg_attribute_line_ids:
                    product_type = "variable"  # Changes by Akash
                    sale_price = str(product_price)
                    for product_tmpl_attributes in record.eg_attribute_line_ids:
                        eg_product_attribute_id = product_tmpl_attributes.eg_product_attribute_id
                        option_list = []
                        for prod_attribute_value in product_tmpl_attributes.eg_value_ids:
                            option_list.append(prod_attribute_value.name)
                        if not eg_product_attribute_id.inst_attribute_id:  # add by akash
                            data = {'name': eg_product_attribute_id.name, }
                            woo_attribute_data = wcapi.post("products/attributes", data)
                            if woo_attribute_data.status_code == 201:
                                woo_attribute_data = woo_attribute_data.json()
                            elif woo_attribute_data.status_code == 400:
                                woo_attribute_data = self.env["eg.product.attribute"].import_attribute(
                                    instance_id=woo_api, eg_product_attribute_id=eg_product_attribute_id)
                            eg_product_attribute_id.write({
                                'inst_attribute_id': str(woo_attribute_data.get("id")),
                                'slug': woo_attribute_data.get("slug"),
                                'type': woo_attribute_data.get("type"),
                                'order_by': woo_attribute_data.get("order_by"),
                                'has_archives': woo_attribute_data.get("has_archives"), })
                            for eg_value_id in product_tmpl_attributes.eg_value_ids:
                                value_data = {'name': eg_value_id.name, }
                                woo_term_id = wcapi.post(
                                    "products/attributes/{}/terms".format(
                                        eg_product_attribute_id.inst_attribute_id), value_data)
                                if woo_term_id.status_code == 201:
                                    woo_term_id = woo_term_id.json()
                                    eg_value_id.write({'instance_value_id': woo_term_id.get('id'),
                                                       'slug': woo_term_id.get('slug'),
                                                       'description': woo_term_id.get('description'),
                                                       'menu_order': woo_term_id.get('menu_order'),
                                                       'count': woo_term_id.get('count'), })

                        prod_attribute = {'id': int(eg_product_attribute_id.inst_attribute_id),
                                          'name': product_tmpl_attributes.eg_product_attribute_id.name,
                                          'options': option_list,
                                          'variation': True,
                                          'visible': True, }
                        attribute_lines.append(prod_attribute)

                else:  # Changes by Akash
                    product_type = "simple"
                    sale_price = str(record.price)

                data = {'name': record.name,
                        'type': product_type,
                        'slug': str(record.slug),
                        'permalink': record.permalink,
                        'status': record.status,
                        'catalog_visibility': record.catalog_visibility,
                        'sku': record.default_code and str(record.default_code) or "",
                        'price': str(record.product_price),
                        'regular_price': str(record.regular_price),
                        'sale_price': sale_price,  #
                        'on_sale': record.sale_ok,
                        'purchasable': record.purchase_ok,
                        'total_sales': record.sale_count,
                        'external_url': str(record.external_url),
                        'button_text': str(record.button_text),
                        'tax_status': str(record.tax_status),
                        'tax_class': str(record.tax_class),
                        'manage_stock': record.manage_stock,
                        'stock_quantity': record.qty_available,
                        'stock_status': record.stock_status,
                        'backorders': record.backorders,
                        'backorders_allowed': record.backorders_allowed,
                        'backordered': record.backordered,
                        'sold_individually': record.sold_individually,
                        'shipping_required': record.shipping_required,
                        'shipping_taxable': record.shipping_taxable,
                        'shipping_class': str(record.shipping_class),
                        'shipping_class_id': record.shipping_class_id,
                        'reviews_allowed': record.reviews_allowed,
                        'average_rating': record.average_rating,
                        'rating_count': record.rating_count,
                        'weight': str(record.weight),
                        'attributes': attribute_lines, }
                if record.eg_category_ids:
                    category_data_list = []
                    for eg_category_id in record.eg_category_ids:
                        eg_category_id = self.export_category_woocommerce(instance_id=woo_api,
                                                                          wcapi=wcapi,
                                                                          eg_category_id=eg_category_id)
                        category_data_list.append({"id": eg_category_id.instance_product_category_id})

                    data.update({"categories": category_data_list})

                woo_prod_tmpl = wcapi.post("products", data).json()

                if not woo_prod_tmpl.get("data"):
                    record.write({'inst_product_tmpl_id': str(woo_prod_tmpl.get("id")),
                                  'is_woocommerce_tmpl_product': True,
                                  'update_required': False,
                                  'woo_product_tmpl_type': product_type})
                    if record.eg_attribute_line_ids:
                        # Product template with his variant export to WC
                        record.eg_product_ids.woo_odoo_product_product_export()  # Changes by Akash

                    else:
                        # No required call method  product variant export for without variant product
                        record.eg_product_ids[0].write({"inst_product_id": str(woo_prod_tmpl.get('id')),
                                                        "is_woocommerce_product": True,
                                                        'update_required': False, })  # Changes by Akash
                    status = "yes"
                    text = "This product is successfully export to woocommerce"
                else:
                    partial = True
                    text = "{}".format(woo_prod_tmpl.get("message"))
                    _logger.info(
                        "Export Product Template - ({}) : {}".format(record.name, woo_prod_tmpl.get("message")))
                eg_history_id = self.env["eg.sync.history"].create({"error_message": text,
                                                                    "status": status,
                                                                    "process_on": "product",
                                                                    "process": "b",
                                                                    "instance_id": woo_api.id,
                                                                    "product_id": record.odoo_product_tmpl_id.id,
                                                                    "child_id": True})
                history_id_list.append(eg_history_id.id)
        if partial:
            status = "partial"
            text = "Some product was exported and some product is not exported"
        if status == "yes" and not partial:
            text = "All product was successfully exported in woocommerce"
        if not history_id_list:
            status = "yes"
            text = "All product was already export to woocommerce"
        self.env["eg.sync.history"].create({"error_message": text,
                                            "status": status,
                                            "process_on": "product",
                                            "process": "b",
                                            "instance_id": eg_product_tmpl_ids and eg_product_tmpl_ids[
                                                0].instance_id.id or None,
                                            "parent_id": True,
                                            "eg_history_ids": [(6, 0, history_id_list)]})

    def export_category_woocommerce(self, wcapi=None, instance_id=None, eg_category_id=None):
        """
        In this export category to bigcommerce and create mapping
        :param wcapi: WooCommerce library
        :param instance_id: Browseable object of instance
        :param eg_category_id: Browseable object of mapping category
        :return: Browseable object of mapping category
        """
        if not eg_category_id.instance_product_category_id:
            category_data = {'name': eg_category_id.name, 'count': eg_category_id.count,
                             'slug': eg_category_id.name.lower()}
            if eg_category_id.real_parent_id or eg_category_id.odoo_category_id.parent_id:
                if eg_category_id.parent_id:
                    category_data.update(
                        {"parent": eg_category_id.parent_id})

                else:
                    parent_category_id = self.env["eg.product.category"].search([("instance_id", "=", instance_id.id), (
                        "odoo_category_id", "=", eg_category_id.odoo_category_id.parent_id.id)])
                    if not parent_category_id:
                        parent_category_id = self.env["eg.product.category"].create({
                            'instance_id': instance_id.id,
                            'instance_product_category_id': 0,
                            'name': eg_category_id.odoo_category_id.parent_id.name,
                            'odoo_category_id': eg_category_id.odoo_category_id.parent_id.id, })
                        self.export_category_woocommerce(eg_category_id=parent_category_id,
                                                         wcapi=wcapi, instance_id=instance_id)
                    elif not parent_category_id.instance_product_category_id:
                        self.export_category_woocommerce(eg_category_id=parent_category_id,
                                                         wcapi=wcapi, instance_id=instance_id)
                    category_data.update(
                        {"parent": str(parent_category_id.instance_product_category_id)})
                    eg_category_id.write({"parent_id": str(parent_category_id.instance_product_category_id),
                                          "real_parent_id": parent_category_id.id})
            response = None
            try:
                response = wcapi.post("products/categories", category_data)
                success = True
            except Exception as e:
                success = False
            if success and response.status_code == 201:
                response = response.json()

            elif success and response.status_code == 409:
                response = self.env["eg.product.category"].import_product_category(
                    instance_id=instance_id, eg_category_id=eg_category_id)

                eg_category_id.write({'instance_product_category_id': response.get("id"),
                                      'slug': response.get("slug"),
                                      'description': response.get("description"),
                                      'display': response.get("display"),
                                      'menu_order': response.get("menu_order"), })
                return eg_category_id
            else:
                return eg_category_id
        else:
            return eg_category_id

    def export_update_product_template_middle_to_wc(self, instance_id=None):  # Make method by akash
        """
        In this method update product from middle layer to bigcommerce with category
        :param instance_id: Browseable object of instance
        :return: Nothing
        """
        status = "no"
        text = ""
        partial = False
        history_id_list = []
        eg_product_tmpl_ids = self
        if not eg_product_tmpl_ids:
            eg_product_tmpl_ids = self.search(
                [("instance_id", "=", instance_id.id), ("inst_product_tmpl_id", "not in", [False, ""]),
                 ("update_required", "=", True)])
        else:
            eg_product_tmpl_ids = eg_product_tmpl_ids.filtered(lambda l: l.inst_product_tmpl_id)
        for eg_product_tmpl_id in eg_product_tmpl_ids:
            woo_api = eg_product_tmpl_id.instance_id
            try:  # Changes by Akash
                wcapi = woo_api.get_wcapi_connection()
            except Exception as e:
                raise Warning("{}".format(e))
            status = "no"
            data = {'name': eg_product_tmpl_id.name,
                    'status': eg_product_tmpl_id.status,
                    'catalog_visibility': eg_product_tmpl_id.catalog_visibility,
                    'sku': eg_product_tmpl_id.default_code and str(eg_product_tmpl_id.default_code) or "",
                    'price': str(eg_product_tmpl_id.product_price),
                    'regular_price': str(eg_product_tmpl_id.regular_price),
                    'sale_price': str(eg_product_tmpl_id.price),  #
                    'on_sale': eg_product_tmpl_id.sale_ok,
                    'purchasable': eg_product_tmpl_id.purchase_ok,
                    'tax_status': str(eg_product_tmpl_id.tax_status),
                    'manage_stock': eg_product_tmpl_id.manage_stock,
                    'stock_quantity': eg_product_tmpl_id.qty_available,
                    'stock_status': eg_product_tmpl_id.stock_status,
                    'backorders': eg_product_tmpl_id.backorders,
                    'weight': str(eg_product_tmpl_id.weight), }
            if eg_product_tmpl_id.eg_category_ids:
                category_data_list = []
                for eg_category_id in eg_product_tmpl_id.eg_category_ids:
                    eg_category_id = self.export_category_woocommerce(instance_id=woo_api,
                                                                      wcapi=wcapi,
                                                                      eg_category_id=eg_category_id)
                    category_data_list.append({"id": eg_category_id.instance_product_category_id})

                data.update({"categories": category_data_list})
            response = wcapi.put('products/{}'.format(eg_product_tmpl_id.inst_product_tmpl_id), data)
            if response.status_code == 200:
                eg_product_tmpl_id.write({"update_required": False})
                if eg_product_tmpl_id.woo_product_tmpl_type == "variable":
                    for eg_product_id in eg_product_tmpl_id.eg_product_ids:
                        if not eg_product_id.update_required:
                            continue
                        data = {'sku': eg_product_id.default_code or "",
                                'regular_price': str(eg_product_id.product_regular_price),
                                'price': str(eg_product_id.price),
                                'on_sale': eg_product_id.on_sale,
                                'purchasable': eg_product_id.purchasable,
                                'description': eg_product_id.description and str(eg_product_id.description) or "",
                                'permalink': eg_product_id.permalink,
                                'tax_status': eg_product_id.tax_status,
                                'tax_class': str(eg_product_id.tax_class),
                                'manage_stock': eg_product_id.manage_stock,
                                'stock_quantity': eg_product_id.qty_available,
                                'stock_status': eg_product_id.stock_status,
                                'backorders': eg_product_id.backorders,
                                'backorders_allowed': eg_product_id.backorders_allowed,
                                'backordered': eg_product_id.backordered,
                                'weight': str(eg_product_id.weight),
                                "dimensions": {
                                    "length": str(eg_product_id.product_length),
                                    "width": str(eg_product_id.product_width),
                                    "height": str(eg_product_id.product_height),
                                },
                                "shipping_class": str(eg_product_id.shipping_class),
                                "shipping_class_id": eg_product_id.shipping_class_id,
                                }
                        response = wcapi.put(
                            "products/{}/variations/{}".format(eg_product_tmpl_id.inst_product_tmpl_id,
                                                               eg_product_id.inst_product_id), data)
                        if response.status_code != 200:
                            _logger.info("Woo Product Template - ({}) : {}".format(eg_product_id.name, response.text))
                        else:
                            eg_product_id.write({"update_required": False})
                status = "yes"
                text = "This product is successfully update export to woocommerce"
            else:
                text = "{}".format(response.text)
                partial = True
                _logger.info("Woo Product Template - ({}) : {}".format(eg_product_tmpl_id.name, response.text))
            eg_history_id = self.env["eg.sync.history"].create({"error_message": text,
                                                                "status": status,
                                                                "process_on": "product",
                                                                "process": "d",
                                                                "instance_id": woo_api.id,
                                                                "product_id": eg_product_tmpl_id.odoo_product_tmpl_id.id,
                                                                "child_id": True})
            history_id_list.append(eg_history_id.id)
        if partial:
            status = "partial"
            text = "Some product was update and some product is not update at export"
        if status == "yes" and not partial:
            text = "All product was successfully update in woocommerce at export"
        if not history_id_list:
            status = "yes"
            text = "All products are already update"
        self.env["eg.sync.history"].create({"error_message": text,
                                            "status": status,
                                            "process_on": "product",
                                            "process": "d",
                                            "instance_id": eg_product_tmpl_ids and eg_product_tmpl_ids[
                                                0].instance_id.id or None,
                                            "parent_id": True,
                                            "eg_history_ids": [(6, 0, history_id_list)]})

    def update_product_price(self, instance_id):
        """
        In this update product price from woocommerce to odoo and midle layer.
        :param instance_id: Browseable object of instance
        :return: Nothing
        """
        woo_api = instance_id
        try:  # Changes by Akash
            wcapi = woo_api.get_wcapi_connection()
        except Exception as e:
            raise Warning("{}".format(e))
        page = 1
        while page > 0:  # Changes by Akash
            status = "no"
            text = ""
            partial = False
            history_id_list = []
            response = wcapi.get('products', params={'per_page': 100, 'page': page})
            if response.status_code == 200:
                if response.json():
                    page += 1
                    for woo_tmpl_dict in response.json():
                        status = "no"
                        eg_product_tmpl_id = self.search(  # Changes by Akash
                            [('inst_product_tmpl_id', '=', str(woo_tmpl_dict.get("id"))),
                             ("instance_id", "=", woo_api.id)])
                        if eg_product_tmpl_id:
                            eg_product_tmpl_id.write({
                                'regular_price': woo_tmpl_dict.get('regular_price'),
                                'price': woo_tmpl_dict.get('sale_price'),
                            })
                            eg_product_tmpl_id.odoo_product_tmpl_id.write({
                                'list_price': woo_tmpl_dict.get('sale_price'),
                                'standard_price': woo_tmpl_dict.get('regular_price'),
                            })

                            for eg_product_id in eg_product_tmpl_id.eg_product_ids:  # Changes by Akash
                                woo_product_variation_response = wcapi.get(
                                    "products/{}/variations/{}".format(woo_tmpl_dict.get('id'),
                                                                       eg_product_id.inst_product_id)).json()
                                eg_product_id.write(
                                    {'price': woo_product_variation_response.get('sale_price'),
                                     'product_regular_price': woo_product_variation_response.get(
                                         'regular_price'), })
                                eg_product_id.odoo_product_id.write(
                                    {'lst_price': woo_product_variation_response.get('sale_price') and float(
                                        woo_product_variation_response.get('sale_price')) or 0,
                                     'standard_price': woo_product_variation_response.get('regular_price') and float(
                                         woo_product_variation_response.get('regular_price')) or 0, })
                            status = "yes"
                            text = "This product is successfully update price"
                            eg_history_id = self.env["eg.sync.history"].create({"error_message": text,
                                                                                "status": status,
                                                                                "process_on": "product",
                                                                                "process": "c",
                                                                                "instance_id": woo_api.id,
                                                                                "product_id": eg_product_tmpl_id.odoo_product_tmpl_id.id,
                                                                                "child_id": True})
                            history_id_list.append(eg_history_id.id)
                        else:
                            _logger.info(
                                "{} not imported in odoo so please import first!!!".format(woo_tmpl_dict.get('name')))
                    if partial:
                        status = "partial"
                        text = "Some product was update price and some product is not update price at export"
                    if status == "yes" and not partial:
                        text = "All product was successfully update price in woocommerce at export"
                    if not history_id_list:
                        text = "Any product is not import in middle layer and odoo"
                    self.env["eg.sync.history"].create({"error_message": text,
                                                        "status": status,
                                                        "process_on": "product",
                                                        "process": "c",
                                                        "instance_id": woo_api.id,
                                                        "parent_id": True,
                                                        "eg_history_ids": [(6, 0, history_id_list)]})
                else:
                    break
            else:
                raise ValidationError("{}".format(response.text))

    def update_product_stock(self, instance_id):
        """
        In this method update product stock from woocommerce to odoo and middle layer.
        :param instance_id: Browseable object of instance
        :return: Nothing
        """
        woo_api = instance_id
        try:  # Changes by Akash
            wcapi = woo_api.get_wcapi_connection()
        except Exception as e:
            raise Warning("{}".format(e))
        page = 1
        while page > 0:
            status = "no"
            text = ""
            partial = False
            history_id_list = []
            response = wcapi.get('products', params={'per_page': 100, 'page': page})
            if response.status_code == 200:
                if response.json():
                    page += 1
                    for woo_tmpl_dict in response.json():
                        status = "no"
                        eg_product_tmpl_id = self.search(  # Changes by Akash
                            [('inst_product_tmpl_id', '=', str(woo_tmpl_dict.get("id"))),
                             ("instance_id", "=", woo_api.id)])
                        if eg_product_tmpl_id:
                            eg_product_tmpl_id.write({'manage_stock': woo_tmpl_dict.get('manage_stock'),
                                                      'qty_available': woo_tmpl_dict.get('stock_quantity'),
                                                      'stock_status': woo_tmpl_dict.get('stock_status'), })
                            eg_product_tmpl_id.odoo_product_tmpl_id.write(
                                {'qty_available': woo_tmpl_dict.get('stock_quantity'), })

                            for eg_product_id in eg_product_tmpl_id.eg_product_ids:  # Changes by Akash
                                woo_product_variation_response = wcapi.get(
                                    "products/{}/variations/{}".format(woo_tmpl_dict.get('id'),
                                                                       eg_product_id.inst_product_id)).json()
                                eg_product_id.write({
                                    'stock_status': woo_product_variation_response.get('stock_status'),
                                    'qty_available': woo_product_variation_response.get('stock_quantity'),
                                    'manage_stock': woo_product_variation_response.get('manage_stock'), })
                                eg_product_id.odoo_product_id.write({
                                    'qty_available': woo_product_variation_response.get('stock_quantity'), })
                            status = "yes"
                            text = "This product is successfully update stock"
                            eg_history_id = self.env["eg.sync.history"].create({"error_message": text,
                                                                                "status": status,
                                                                                "process_on": "product",
                                                                                "process": "c",
                                                                                "instance_id": woo_api.id,
                                                                                "product_id": eg_product_tmpl_id.odoo_product_tmpl_id.id,
                                                                                "child_id": True})
                            history_id_list.append(eg_history_id.id)
                        else:
                            _logger.info(
                                "{} not imported in odoo so please import first!!!".format(woo_tmpl_dict.get('name')))
                    if partial:
                        status = "partial"
                        text = "Some product was update stock and some product is not update stock at export"
                    if status == "yes" and not partial:
                        text = "All product was successfully update stock in woocommerce at export"
                    if not history_id_list:
                        text = "Any product is not import in middle layer and odoo"
                    self.env["eg.sync.history"].create({"error_message": text,
                                                        "status": status,
                                                        "process_on": "product",
                                                        "process": "c",
                                                        "instance_id": woo_api.id,
                                                        "parent_id": True,
                                                        "eg_history_ids": [(6, 0, history_id_list)]})
                else:
                    break
            else:
                raise ValidationError("{}".format(response.text))

    def update_product_tmpl_price(self):
        """
        In this update product price from middle layer to woocommerce with variant.
        :return: Nothing
        """
        status = "no"
        text = ""
        partial = False
        history_id_list = []
        for rec in self:
            woo_api = self.instance_id
            try:  # Changes by Akash
                wcapi = woo_api.get_wcapi_connection()
            except Exception as e:
                raise Warning("{}".format(e))
            status = "no"
            if not rec.no_export_woo and rec.is_woocommerce_tmpl_product:  # Changes by Akash
                data = {'regular_price': str(rec.regular_price),
                        'sale_price': str(rec.price), }
                response = wcapi.put("products/{}".format(rec.inst_product_tmpl_id), data)
                if response.status_code == 200:  # Changes by Akash
                    if rec.woo_product_tmpl_type == "variable":  # Changes by Akash
                        rec.eg_product_ids.update_woo_product_price()
                    status = "yes"
                    text = "This product is successfully update product price"
                else:
                    text = "{}".format(response.text)
                    partial = True
            else:
                text = "This product is not export in woocommerce"
                partial = True
                _logger.info("{} not Export because you check not export in woocommerce".format(rec.name))
            eg_history_id = self.env["eg.sync.history"].create({"error_message": text,
                                                                "status": status,
                                                                "process_on": "product",
                                                                "process": "d",
                                                                "instance_id": woo_api.id,
                                                                "product_id": rec.odoo_product_tmpl_id.id,
                                                                "child_id": True})
            history_id_list.append(eg_history_id.id)
        if partial:
            status = "partial"
            text = "Some product was update price and some product is not update price at export"
        if status == "yes" and not partial:
            text = "All product was successfully update price in woocommerce at export"
        self.env["eg.sync.history"].create({"error_message": text,
                                            "status": status,
                                            "process_on": "product",
                                            "process": "d",
                                            "parent_id": True,
                                            "eg_history_ids": [(6, 0, history_id_list)]})

    def update_woo_product_tmpl_stock(self, from_action=None):
        """
        In this update product stock from odoo to WooCommerce with variant.
        :param from_action: True or False
        :return: Nothing
        """
        status = "no"
        text = ""
        partial = False
        history_id_list = []
        for rec in self:
            woo_api = rec.instance_id
            try:  # Changes by Akash
                wcapi = woo_api.get_wcapi_connection()
            except Exception as e:
                raise Warning("{}".format(e))
            status = "no"
            if not rec.no_export_woo and rec.is_woocommerce_tmpl_product:  # Changes by Akash
                if rec.woo_product_tmpl_type == "simple":
                    stock = rec.odoo_product_tmpl_id.qty_available - rec.odoo_product_tmpl_id.outgoing_qty
                    if stock:
                        stock_status = "instock"
                    else:
                        stock_status = "outofstock"
                    data = {
                        'manage_stock': rec.manage_stock,
                        'stock_quantity': stock,
                        'stock_status': stock_status,
                    }
                    response = wcapi.put("products/{}".format(rec.inst_product_tmpl_id), data)
                    if response.status_code == 200:  # Changes by Akash

                        status = "yes"
                        text = "This product is successfully update product stock"
                    else:
                        text = "{}".format(response.text)
                        partial = True
                elif from_action:
                    rec.eg_product_ids.update_woo_product_stock(from_action=True)
                    status = "yes"
                    text = "This product is successfully update product stock"
            else:
                text = "This product is not export in woocommerce"
                partial = True
                _logger.info("{} not Export because you check not export in woocommerce".format(rec.name))
            eg_history_id = self.env["eg.sync.history"].create({"error_message": text,
                                                                "status": status,
                                                                "process_on": "product",
                                                                "process": "d",
                                                                "instance_id": woo_api.id,
                                                                "product_id": rec.odoo_product_tmpl_id.id,
                                                                "child_id": True})
            history_id_list.append(eg_history_id.id)
        if partial:
            status = "partial"
            text = "Some product was update stock and some product is not update stock at export"
        if status == "yes" and not partial:
            text = "All product was successfully update stock in woocommerce at export"
        self.env["eg.sync.history"].create({"error_message": text,
                                            "status": status,
                                            "process_on": "product",
                                            "process": "d",
                                            "parent_id": True,
                                            "eg_history_ids": [(6, 0, history_id_list)]})

    def set_image_odoo(self):
        """
        In this set product image from middle layer to odoo product template.
        :return: Nothing
        """
        for record in self:
            if record.product_tmpl_image:
                record.odoo_product_tmpl_id.image_1920 = record.product_tmpl_image

    def create_product_attributes(self, woo_tmpl_dict, woo_api):
        """
        In this create attribute and his value in odoo and middle layer from woocommerce
        :param woo_tmpl_dict: dict of product template data
        :param woo_api: Browseable object of instance
        :return: Nothing
        """
        #  Change code flow and solve some issue by Akash
        product_attribute_obj = self.env['product.attribute']
        product_attribute_value_obj = self.env['product.attribute.value']
        woo_product_attribute_obj = self.env['eg.product.attribute']
        woo_attribute_terms_obj = self.env['eg.attribute.value']
        for attribute_dict in woo_tmpl_dict.get('attributes'):
            odoo_attribute_id = self.env['product.attribute'].search(
                [('name', '=', attribute_dict.get('name'))])
            eg_attribute_id = self.env['eg.product.attribute'].search(
                [('inst_attribute_id', '=', str(attribute_dict.get('id'))), ('instance_id', '=', woo_api.id)])
            if not odoo_attribute_id:
                odoo_attribute_id = product_attribute_obj.create({'name': attribute_dict.get('name')})
                for attribute_value in attribute_dict.get('options'):
                    product_attribute_value_obj.create({'name': attribute_value,
                                                        'attribute_id': odoo_attribute_id.id, })
            else:
                for attribute_value in attribute_dict.get('options'):
                    odoo_attribute_value_id = self.env['product.attribute.value'].search(
                        [('attribute_id', '=', odoo_attribute_id.id), ('name', '=', attribute_value)])
                    if not odoo_attribute_value_id:
                        product_attribute_value_obj.create({'attribute_id': odoo_attribute_id.id,
                                                            'name': attribute_value, })

            if not eg_attribute_id:
                eg_attribute_id = woo_product_attribute_obj.create({'instance_id': woo_api.id,
                                                                    'name': attribute_dict.get('name'),
                                                                    'odoo_attribute_id': odoo_attribute_id.id,
                                                                    'inst_attribute_id': str(
                                                                        attribute_dict.get('id')), })
                for attribute_value in attribute_dict.get('options'):
                    product_attribute_value_id = self.env['product.attribute.value'].search(
                        [('name', '=', attribute_value), ("attribute_id", "=", odoo_attribute_id.id)])
                    woo_attribute_terms_obj.create({'instance_id': woo_api.id,
                                                    'name': attribute_value,
                                                    'inst_attribute_id': eg_attribute_id.id,
                                                    'odoo_attribute_value_id': product_attribute_value_id.id, })
            else:
                for attribute_value in attribute_dict.get('options'):
                    woo_attribute_terms_id = self.env['eg.attribute.value'].search(
                        [('inst_attribute_id', '=', eg_attribute_id.id),
                         ('name', '=', attribute_value), ('instance_id', '=', woo_api.id)])
                    if not woo_attribute_terms_id:
                        product_attribute_value_id = self.env['product.attribute.value'].search(
                            [('name', '=', attribute_value), ("attribute_id", "=", odoo_attribute_id.id)])
                        woo_attribute_terms_obj.create({'instance_id': woo_api.id,
                                                        'inst_attribute_id': eg_attribute_id.id,
                                                        'name': attribute_value,
                                                        'odoo_attribute_value_id': product_attribute_value_id.id, })

    def set_odoo_product_attribute(self, woo_tmpl_dict, woo_api):
        """
        In this find and make list of odoo attribute and his value for attribute line in odoo product.
        :param woo_tmpl_dict: dict of product template data
        :param woo_api: Browseable object of instance
        :return: list of odoo attribute line data
        """
        line_value_list = []
        for product_attribute in woo_tmpl_dict.get("attributes"):
            product_attribute_value_ids = self.env['product.attribute.value']
            eg_attribute_id = self.env['eg.product.attribute'].search(
                [('inst_attribute_id', '=', str(product_attribute.get('id'))), ('instance_id', '=', woo_api.id)])
            for product_attribute_option in product_attribute.get('options'):
                for value_id in eg_attribute_id.odoo_attribute_id.value_ids:
                    if product_attribute_option == value_id.name:
                        product_attribute_value_ids += value_id
            print(product_attribute_value_ids)
            line_value_list.append(
                (0, False, {'attribute_id': eg_attribute_id.odoo_attribute_id.id,
                            'value_ids': [(6, 0, product_attribute_value_ids.ids)]}))
        return line_value_list

    def set_woo_product_attribute(self, woo_tmpl_dict, woo_api):
        """
        In this find and make list of mapping attribute and his value for attribute line in mapping product
        :param woo_tmpl_dict: dict of product template data
        :param woo_api: Browseable object of instance
        :return: list of mapping attribute line data
        """
        woo_line_value_list = []
        for product_attribute in woo_tmpl_dict.get("attributes"):
            eg_value_ids = self.env['eg.attribute.value']
            eg_attribute_id = self.env['eg.product.attribute'].search(
                [('inst_attribute_id', '=', str(product_attribute.get('id'))), ('instance_id', '=', woo_api.id)])
            for product_attribute_option in product_attribute.get('options'):
                for value_id in eg_attribute_id.eg_value_ids:
                    if product_attribute_option == value_id.name:
                        eg_value_ids += value_id
            woo_line_value_list.append(
                (0, False, {'eg_product_attribute_id': eg_attribute_id.id,
                            'eg_value_ids': [(6, 0, eg_value_ids.ids)]}))
        return woo_line_value_list

    def check_new_product_variant_import(self, woo_tmpl_dict=None, eg_product_tmpl_id=None,
                                         woo_api=None):  # Changes by Akash (add method)
        """
        In this when import product and any product is already in odoo so check any new variant is add or not ,
        check attribute value not check attribute.
        :param woo_tmpl_dict: dict of product template data
        :param eg_product_tmpl_id: Browseable object of mapping product template
        :param woo_api: Browseable object of instance
        :return: True or False
        """
        variant_mapping = False
        if woo_tmpl_dict.get("attributes"):
            odoo_product_tmpl_id = eg_product_tmpl_id.odoo_product_tmpl_id
            for woo_attribute in woo_tmpl_dict.get("attributes"):
                value_ids = []
                woo_value_ids = []
                attribute_id = self.env["product.attribute"].search([("name", "=", woo_attribute.get("name"))])
                attribute_line_id = odoo_product_tmpl_id.attribute_line_ids.filtered(
                    lambda l: l.attribute_id == attribute_id)
                if attribute_line_id:
                    eg_attribute_id = self.env['eg.product.attribute'].search(
                        [('inst_attribute_id', '=', str(woo_attribute.get('id'))), ('instance_id', '=', woo_api.id)])
                    for woo_value in woo_attribute.get("options"):
                        value_id = self.env["product.attribute.value"].search(
                            [("name", "=", woo_value), ("attribute_id", "=", attribute_id.id)])
                        if value_id not in attribute_line_id.value_ids:
                            woo_value_id = self.env["eg.attribute.value"].search(
                                [('inst_attribute_id', '=', eg_attribute_id.id),
                                 ('name', '=', woo_value), ('instance_id', '=', woo_api.id)])
                            value_ids.append(value_id.id)
                            woo_value_ids.append(woo_value_id.id)
                    if value_ids:
                        variant_mapping = True
                        woo_attribute_line_id = eg_product_tmpl_id.eg_attribute_line_ids.filtered(
                            lambda l: l.eg_product_attribute_id == eg_attribute_id)
                        for value_id in value_ids:
                            attribute_line_id.write({"value_ids": [(4, value_id, 0)]})
                        for woo_value_id in woo_value_ids:
                            woo_attribute_line_id.write({"eg_value_ids": [(4, woo_value_id, 0)]})

        return variant_mapping

    def check_product_attribute_import(self, woo_tmpl_dict=None,
                                       odoo_product_tmpl_id=None, ):  # Changes by Akash (add method)
        """
        In this check attribute value of odoo product and woocommerce product sem or not
        :param woo_tmpl_dict: dict of product template data
        :param odoo_product_tmpl_id: Browseable object of odoo product template
        :return: True or False
        """
        if woo_tmpl_dict.get("attributes"):
            for woo_attribute in woo_tmpl_dict.get("attributes"):
                attribute_id = self.env["product.attribute"].search([("name", "=", woo_attribute.get("name"))])
                if attribute_id:
                    attribute_value_ids = self.env["product.attribute.value"].search(
                        [("name", "in", woo_attribute.get("options")), ("attribute_id", "=", attribute_id.id)])
                    compare_values = odoo_product_tmpl_id.attribute_line_ids.filtered(
                        lambda l: l.value_ids == attribute_value_ids)
                    if not compare_values:
                        return False
            return True
        else:
            return False
