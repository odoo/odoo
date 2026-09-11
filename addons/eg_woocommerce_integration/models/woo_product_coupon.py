import logging

from odoo import fields, models

_logger = logging.getLogger("===+++ Woo Product Coupon +++===")


class WooProductCoupon(models.Model):
    _name = 'woo.product.coupon'

    instance_id = fields.Many2one(comodel_name='eg.ecom.instance')
    provider = fields.Selection(related="instance_id.provider", store=True)
    woo_coupon_id = fields.Integer(string='WC Coupon ID')
    coupon_code = fields.Char(string='Code')
    coupon_amount = fields.Float(string='Coupon Amount')
    discount_type = fields.Selection([('percent', 'Percent'), ('fixed_cart', 'Fixed Cart')])
    description = fields.Char(string='Description')
    date_expires = fields.Char(string='Date Expire')
    usage_count = fields.Integer(string='Used coupon Count')
    individual_use = fields.Boolean(string='Use Individual')
    product_tmpl_ids = fields.Many2many('eg.product.template', 'product_tmpl_ids_rel', string='Product Template Ids')
    excluded_product_tmpl_ids = fields.Many2many('eg.product.template', 'excluded_product_tmpl_ids_rel',
                                                 string='Exclude Product Template')
    usage_limit = fields.Integer(string='Coupon use Total')
    usage_limit_per_user = fields.Integer(string='Per user Coupon')
    limit_usage_to_x_items = fields.Integer(string='Required Items',
                                            help="Max number of items in the cart the coupon can be applied")
    free_shipping = fields.Boolean(string='Free Shipping')
    woo_product_categories_ids = fields.Many2many('eg.product.category', 'product_categories_rel',
                                                  string='Product Categories')
    excluded_product_categories_ids = fields.Many2many('eg.product.category', 'exclude_product_categories_rel',
                                                       string='Not Applied Categories')
    exclude_sale_items = fields.Boolean(string='Not Applied Sale Price')
    minimum_amount = fields.Float(string='Minimum Amount')
    maximum_amount = fields.Float(string='Maximum Amount')
    email_restrictions = fields.Char(string='Email Address')
    woo_user_id = fields.Many2many(comodel_name='eg.res.partner', string='User IDs')

    def import_product_coupon(self, instance_id):
        """
        In this create product coupon in middle layer from woocommerce.
        :param instance_id: Browseable object of instance
        :return: Nothing
        """
        woo_api = instance_id
        try:  # Changes by Akash
            wcapi = woo_api.get_wcapi_connection()
        except Exception as e:
            return {"warning": {"message": (
                "{}".format(e))}}
        coupon_response = wcapi.get("coupons")
        if coupon_response.status_code == 200:
            for woo_product_coupon_dict in coupon_response.json():
                woo_product_coupon_id = self.search(
                    [('woo_coupon_id', '=', woo_product_coupon_dict.get('id')), ('instance_id', '=', woo_api.id)])
                if woo_product_coupon_id:
                    _logger.info("This Coupon is already Imported!!!")
                else:
                    woo_content_list = self.find_content_related_coupon(woo_product_coupon_dict=woo_product_coupon_dict,
                                                                        woo_api=woo_api)
                    self.create([{
                        'instance_id': woo_api.id,
                        'woo_coupon_id': woo_product_coupon_dict.get('id'),
                        'coupon_code': woo_product_coupon_dict.get('code'),
                        'coupon_amount': woo_product_coupon_dict.get('amount'),
                        'discount_type': woo_product_coupon_dict.get('discount_type'),
                        'description': woo_product_coupon_dict.get('description'),
                        'date_expires': woo_product_coupon_dict.get('date_expires'),
                        'usage_count': woo_product_coupon_dict.get('usage_count'),
                        'individual_use': woo_product_coupon_dict.get('individual_use'),
                        'usage_limit': woo_product_coupon_dict.get('usage_limit'),
                        'usage_limit_per_user': woo_product_coupon_dict.get('usage_limit_per_user'),
                        'limit_usage_to_x_items': woo_product_coupon_dict.get('limit_usage_to_x_items'),
                        'free_shipping': woo_product_coupon_dict.get('free_shipping'),
                        'exclude_sale_items': woo_product_coupon_dict.get('exclude_sale_items'),
                        'minimum_amount': woo_product_coupon_dict.get('minimum_amount'),
                        'maximum_amount': woo_product_coupon_dict.get('maximum_amount'),
                        'email_restrictions': ",".join(woo_product_coupon_dict.get("email_restrictions")),
                        'product_tmpl_ids': woo_content_list[0],
                        'woo_product_categories_ids': woo_content_list[2],
                        'excluded_product_tmpl_ids': woo_content_list[1],
                        'excluded_product_categories_ids': woo_content_list[3],
                    }])
        else:
            return {"warning": {"message": (
                "{}".format(coupon_response.text))}}

    def import_update_product_coupon(self, instance_id):
        """
        In this update product coupon form woocommerce to middle layer.
        :param instance_id: Browseable object of instance
        :return: Nothing
        """
        woo_api = instance_id
        try:  # Changes by Akash
            wcapi = woo_api.get_wcapi_connection()
        except Exception as e:
            return {"warning": {"message": (
                "{}".format(e))}}
        coupon_response = wcapi.get("coupons")
        if coupon_response.status_code == 200:
            for woo_product_coupon_dict in coupon_response.json():
                woo_product_coupon_id = self.search(
                    [('woo_coupon_id', '=', woo_product_coupon_dict.get('id')), ('instance_id', '=', woo_api.id)])
                if woo_product_coupon_id:
                    woo_content_list = self.find_content_related_coupon(woo_product_coupon_dict=woo_product_coupon_dict,
                                                                        woo_api=woo_api)  # Changes by Akash

                    woo_product_coupon_id.write({
                        'coupon_code': woo_product_coupon_dict.get('code'),
                        'coupon_amount': woo_product_coupon_dict.get('amount'),
                        'discount_type': woo_product_coupon_dict.get('discount_type'),
                        'description': woo_product_coupon_dict.get('description'),
                        'date_expires': woo_product_coupon_dict.get('date_expires'),
                        'usage_count': woo_product_coupon_dict.get('usage_count'),
                        'individual_use': woo_product_coupon_dict.get('individual_use'),
                        'usage_limit': woo_product_coupon_dict.get('usage_limit'),
                        'usage_limit_per_user': woo_product_coupon_dict.get('usage_limit_per_user'),
                        'limit_usage_to_x_items': woo_product_coupon_dict.get('limit_usage_to_x_items'),
                        'free_shipping': woo_product_coupon_dict.get('free_shipping'),
                        'exclude_sale_items': woo_product_coupon_dict.get('exclude_sale_items'),
                        'minimum_amount': woo_product_coupon_dict.get('minimum_amount'),
                        'maximum_amount': woo_product_coupon_dict.get('maximum_amount'),
                        'email_restrictions': ",".join(woo_product_coupon_dict.get("email_restrictions")),
                        'product_tmpl_ids': woo_content_list[0],
                        'woo_product_categories_ids': woo_content_list[2],
                        'excluded_product_tmpl_ids': woo_content_list[1],
                        'excluded_product_categories_ids': woo_content_list[3],
                    })
                else:
                    _logger.info("sorry {} coupon not import so first import please!!!".format(
                        woo_product_coupon_dict.get('code')))
        else:
            return {"warning": {"message": (
                "{}".format(coupon_response.text))}}

    def find_content_related_coupon(self, woo_product_coupon_dict=None, woo_api=None):  # Create by Akash
        """
        In this collect list for include product template of coupon, exclude product template of coupon,
        include product category of coupon, exclude product category of coupon.
        :param woo_product_coupon_dict: Dict of product coupon date
        :param woo_api: Browseable object of instance
        :return: List of list which exclude product template for  mapping include product template,
        mapping exclude product template, mapping include product category and mapping exclude product category
        """
        all_content_list = []
        woo_product_tmpl_list = []
        woo_exclude_product_tmpl_list = []
        woo_categ_list = []
        woo_exclude_categ_list = []
        for eg_product_id in woo_product_coupon_dict.get('product_ids'):
            eg_product_tmpl_id = self.env['eg.product.template'].search(
                [('inst_product_tmpl_id', '=', str(eg_product_id)), ('instance_id', '=', woo_api.id)])
            if not eg_product_tmpl_id:
                try:
                    self.env['eg.product.template'].import_product_template(eg_product_id=eg_product_id,
                                                                            instance_id=woo_api)
                except Exception as e:
                    _logger.info("Import Product - ({}) : {}".format(eg_product_id, e))
                eg_product_tmpl_id = self.env['eg.product.template'].search(
                    [('inst_product_tmpl_id', '=', str(eg_product_id)), ('instance_id', '=', woo_api.id)])
            if eg_product_tmpl_id:  # Changes by Akash
                woo_product_tmpl_list.append(eg_product_tmpl_id.id)

        for woo_exclude_product_id in woo_product_coupon_dict.get('excluded_product_ids'):
            eg_product_tmpl_id = self.env['eg.product.template'].search(
                [('inst_product_tmpl_id', '=', str(woo_exclude_product_id)), ('instance_id', '=', woo_api.id)])
            if not eg_product_tmpl_id:
                try:
                    self.env['eg.product.template'].import_product_template(
                        eg_product_id=woo_exclude_product_id, instance_id=woo_api)
                except Exception as e:
                    _logger.info("Import Product - ({}) : {}".format(woo_exclude_product_id, e))
                eg_product_tmpl_id = self.env['eg.product.template'].search(
                    [('inst_product_tmpl_id', '=', str(woo_exclude_product_id)),
                     ('instance_id', '=', woo_api.id)])
            if eg_product_tmpl_id:  # Changes by Akash
                woo_exclude_product_tmpl_list.append(eg_product_tmpl_id.id)

        for woo_categ in woo_product_coupon_dict.get('product_categories'):
            woo_categ_id = self.env['eg.product.category'].search(
                [('instance_product_category_id', '=', woo_categ), ('instance_id', '=', woo_api.id)])
            if not woo_categ_id:
                try:  # Changes by Akash
                    self.env['eg.product.category'].import_product_category(woo_categ_id=woo_categ,
                                                                            instance_id=woo_api)
                except Exception as e:
                    _logger.info("Import Category - ({}) : {}".format(woo_categ, e))
                woo_categ_id = self.env['eg.product.category'].search(
                    [('instance_product_category_id', '=', woo_categ), ('instance_id', '=', woo_api.id)])
            if woo_categ_id:  # Changes by Akash
                woo_categ_list.append(woo_categ_id.id)

        for woo_exclude_category in woo_product_coupon_dict.get('excluded_product_categories'):
            woo_categ_id = self.env['eg.product.category'].search(
                [('instance_product_category_id', '=', woo_exclude_category),
                 ('instance_id', '=', woo_api.id)])
            if not woo_categ_id:
                try:  # Changes by Akash
                    self.env['eg.product.category'].import_product_category(
                        woo_categ_id=woo_exclude_category,
                        instance_id=woo_api)
                except Exception as e:
                    _logger.info("Import Category - ({}) : {}".format(woo_exclude_category, e))
                woo_categ_id = self.env['eg.product.category'].search(
                    [('instance_product_category_id', '=', woo_exclude_category),
                     ('instance_id', '=', woo_api.id)])
            if woo_categ_id:  # Changes by Akash
                woo_exclude_categ_list.append(woo_categ_id.id)
        all_content_list.append(woo_product_tmpl_list)
        all_content_list.append(woo_exclude_product_tmpl_list)
        all_content_list.append(woo_categ_list)
        all_content_list.append(woo_exclude_categ_list)
        return all_content_list
