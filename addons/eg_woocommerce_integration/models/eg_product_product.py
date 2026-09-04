import logging
from datetime import datetime

from odoo import fields, models
from odoo.exceptions import ValidationError

_logging = logging.getLogger("===+++ eCom Product Product +++===")


class EgProductProduct(models.Model):
    _inherit = 'eg.product.product'

    not_export_woo = fields.Boolean(string='No Export WC')
    is_woocommerce_product = fields.Boolean(string='Available in WC')
    description = fields.Text(string="Description")
    permalink = fields.Char(string="Permalink")
    product_regular_price = fields.Float(string="Product Regular Price")
    on_sale = fields.Boolean(string="Can be Sold")
    status = fields.Selection(
        [("draft", "Draft"), ("pending", "Pending"), ("private", "Private"), ("publish", "Publish"),
         ("importing", "Importing")], string="Status")
    purchasable = fields.Boolean(string="Can be Purchased")
    virtual = fields.Boolean(string="Virtual")

    date_on_sale_from = fields.Char(string="Sale start date")
    date_on_sale_to = fields.Char(string="Sale end date")

    tax_status = fields.Selection([("taxable", "Taxable"), ("shipping", "Shipping"), ("none", "None")])
    tax_class = fields.Char(string="Tax class")

    manage_stock = fields.Boolean(string="Manage Stock")
    stock_status = fields.Selection(
        [("instock", "In stock"), ("outofstock", "Out of stock"), ("onbackorder", "On BackOrder")])

    backorders = fields.Selection([("no", "No"), ("notify", "Notify"), ("yes", "Yes")])
    backorders_allowed = fields.Boolean(string="Backorder Allowed")
    backordered = fields.Boolean(string="Backordered")

    product_length = fields.Float(string="Length")
    product_width = fields.Float(string="Width")
    product_height = fields.Float(string="Height")

    shipping_class = fields.Char(string="Shipping Class")
    shipping_class_id = fields.Integer(string="Shipping Class ID")
    menu_order = fields.Integer(string="Menu Order")
    woo_product_image_src = fields.Char(string='Image Src')

    def woo_odoo_product_product_export(self):
        """
        In this export product variant middle layer to woocommerce and set woocommerce id in middle layer.
        :return: Nothing
        """
        woo_api = self[0].instance_id
        try:  # Changes by Akash
            wcapi = woo_api.get_wcapi_connection()
        except Exception as e:
            raise Warning("{}".format(e))
        for record in self:
            if not record.is_woocommerce_product:
                if not record.eg_tmpl_id.inst_product_tmpl_id:
                    raise ValidationError("First Import this Variation Product Template")
                else:
                    eg_product_pricelist_id = self.env['eg.product.pricelist'].search(
                        [('id', '=', woo_api.eg_product_pricelist_id.id)])
                    product_price = None
                    if eg_product_pricelist_id:
                        for woo_product_pricelist_line in eg_product_pricelist_id.eg_product_pricelist_line_ids:
                            if record.id == woo_product_pricelist_line.eg_product_id.id:
                                product_price = woo_product_pricelist_line.price_unit
                                break
                            else:
                                product_price = record.price

                    attribute_list = []
                    for attribute_terms_id in record.eg_value_ids:
                        eg_attribute_id = {"id": int(attribute_terms_id.inst_attribute_id.inst_attribute_id),
                                           "option": attribute_terms_id.name,
                                           }
                        attribute_list.append(eg_attribute_id)
                    data = {'sku': record.default_code or "",
                            'regular_price': str(record.product_regular_price),
                            'sale_price': str(product_price),
                            'on_sale': record.on_sale,
                            'purchasable': record.purchasable,
                            'description': record.description and str(record.description) or "",
                            'permalink': record.permalink,
                            'tax_status': record.tax_status,
                            'tax_class': str(record.tax_class),
                            'manage_stock': record.manage_stock,
                            'stock_quantity': record.qty_available,
                            'stock_status': record.stock_status,
                            'backorders': record.backorders,
                            'backorders_allowed': record.backorders_allowed,
                            'backordered': record.backordered,
                            'weight': str(record.weight),
                            "dimensions": {
                                "length": str(record.product_length),
                                "width": str(record.product_width),
                                "height": str(record.product_height),
                            },
                            "shipping_class": str(record.shipping_class),
                            "shipping_class_id": record.shipping_class_id,
                            "attributes": attribute_list,
                            }
                    woo_product_response = wcapi.post(
                        "products/{}/variations".format(record.eg_tmpl_id.inst_product_tmpl_id), data).json()
                    if not woo_product_response.get("data"):  # Changes by Akash
                        record.write({'inst_product_id': str(woo_product_response.get('id')),
                                      'update_required': False,
                                      'is_woocommerce_product': True, })
                    else:
                        _logging.info(
                            "Export Product - ({}) : {}".format(record.name, woo_product_response.get("message")))
            else:
                _logging.info("{} not Export because you check not export in woocommerce".format(record.name))

    def update_woo_product_price(self):
        """
        In this update product variant price from middle layer to woocommerce.
        :return: Nothing
        """
        woo_api = self[0].instance_id
        try:  # Changes by Akash
            wcapi = woo_api.get_wcapi_connection()
        except Exception as e:
            raise Warning("{}".format(e))
        for rec in self:
            if not rec.not_export_woo and rec.is_woocommerce_product:  # Changes by Akash
                data = {'regular_price': str(rec.product_regular_price),
                        'sale_price': str(rec.price), }
                product_response = wcapi.put(
                    "products/{}/variations/{}".format(rec.eg_tmpl_id.inst_product_tmpl_id,
                                                       rec.inst_product_id),
                    data).json()
            else:
                _logging.info("{} not Export because you check not export in woocommerce".format(rec.name))

    def export_product_stock_by_cron(self):

        """Add method by akash
        for update stock at export by cron and take product by change in stock given datetime"""
        instance_ids = self.env["eg.ecom.instance"].search([('provider', '=', 'eg_woocommerce')])
        for instance_id in instance_ids:
            if instance_id.export_stock_date:
                product_ids = self.env["stock.move"].search([("date", ">=", instance_id.export_stock_date)]).mapped(
                    "product_id")
                instance_id.write({"export_stock_date": datetime.now()})
                eg_product_ids = self.search(
                    [("instance_id", "=", instance_id.id), ("odoo_product_id", "in", product_ids.ids)])
            else:
                eg_product_ids = self.search([("instance_id", "=", instance_id.id)])
                instance_id.write({"export_stock_date": datetime.now()})
            if eg_product_ids:
                eg_product_tmpl_ids = list(dict.fromkeys(eg_product_ids.filtered(
                    lambda l: l.eg_tmpl_id.woo_product_tmpl_type == "simple").mapped(
                    "eg_tmpl_id")))
                eg_product_ids.update_woo_product_stock(eg_product_tmpl_ids=eg_product_tmpl_ids)

    def update_woo_product_stock(self, instance_id=None, from_date=None, from_action=None, eg_product_tmpl_ids=None):
        """
        In this update product variant stock from odoo to woocommerce and if given mapping product template so
        update stock for this product template.
        :param instance_id: Browseable object of instance
        :param from_date: Date
        :param from_action: True or False
        :param eg_product_tmpl_ids: Browseable objects of mapping product template
        :return: Nothing
        """
        status = "no"
        text = ""
        partial = False
        history_id_list = []
        if not from_action and instance_id and from_date:
            product_ids = self.env["stock.move"].search([("date", ">=", from_date)]).mapped("product_id")
            eg_product_ids = self.search(
                [("instance_id", "=", instance_id.id), ("odoo_product_id", "in", product_ids.ids)])
            if eg_product_ids:
                eg_product_tmpl_ids = list(dict.fromkeys(eg_product_ids.filtered(
                    lambda l: l.eg_tmpl_id.woo_product_tmpl_type == "simple").mapped(
                    "eg_tmpl_id")))
        else:
            eg_product_ids = self

        woo_api = instance_id or self[0].instance_id
        try:  # Changes by Akash
            wcapi = woo_api.get_wcapi_connection()
        except Exception as e:
            raise Warning("{}".format(e))
        for eg_product_id in eg_product_ids:
            if eg_product_id.eg_tmpl_id.woo_product_tmpl_type == "variable":
                status = "no"
                if not eg_product_id.not_export_woo and eg_product_id.is_woocommerce_product:  # Changes by Akash
                    stock = eg_product_id.odoo_product_id.qty_available - eg_product_id.odoo_product_id.outgoing_qty
                    if stock:
                        stock_status = "instock"
                    else:
                        stock_status = "outofstock"
                    data = {'manage_stock': eg_product_id.manage_stock,
                            'stock_quantity': stock,
                            'stock_status': stock_status}
                    product_response = wcapi.put(
                        "products/{}/variations/{}".format(eg_product_id.eg_tmpl_id.inst_product_tmpl_id,
                                                           eg_product_id.inst_product_id), data)
                    if product_response.status_code == 200:
                        status = "yes"
                        text = "This product variant is successfully stock update:- {}".format(
                            eg_product_id.default_code)
                        _logging.info("This product was update stock at export: {}".format(eg_product_id.name))
                    else:
                        partial = True
                        text = "This product variant is not stock update - ({}) : {}".format(
                            eg_product_id.default_code,
                            product_response.text)
                        _logging.info("This product not update stock - ({}) : {}".format(eg_product_id.name,
                                                                                         product_response.text))
                else:
                    partial = True
                    text = "This product variant is not export because you check not export in woocommerce :- {}".format(
                        eg_product_id.default_code)
                    _logging.info(
                        "{} not Export because you check not export in woocommerce".format(eg_product_id.name))
                eg_history_id = self.env["eg.sync.history"].create({"error_message": text,
                                                                    "status": status,
                                                                    "process_on": "product",
                                                                    "process": "d",
                                                                    "instance_id": woo_api.id,
                                                                    "product_id": eg_product_id.eg_tmpl_id.odoo_product_tmpl_id.id,
                                                                    "child_id": True})
                history_id_list.append(eg_history_id.id)
        if history_id_list:
            if partial:
                status = "partial"
                text = "Some product variant was update stock and some product variant is not update stock at export"
            if status == "yes" and not partial:
                text = "All product variant was successfully update stock in woocommerce at export"
            self.env["eg.sync.history"].create({"error_message": text,
                                                "status": status,
                                                "process_on": "product",
                                                "process": "d",
                                                "instance_id": woo_api.id,
                                                "parent_id": True,
                                                "eg_history_ids": [(6, 0, history_id_list)]})
        if eg_product_tmpl_ids:
            for eg_product_tmpl_id in eg_product_tmpl_ids:
                eg_product_tmpl_id.update_woo_product_tmpl_stock()

    def set_product_image_odoo(self):
        """
        In this set product image from middle layer to odoo.
        :return: Nothing
        """
        for rec in self:
            if rec.product_image:
                rec.odoo_product_id.image_1920 = rec.product_image
