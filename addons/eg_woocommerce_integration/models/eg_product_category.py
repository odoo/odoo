import base64
import logging

import requests

from odoo import fields, models
from odoo.exceptions import ValidationError

_logging = logging.getLogger("===+++ eCom Product Category +++===")


class EgProductCategory(models.Model):
    _inherit = 'eg.product.category'

    slug = fields.Char(string="Slug")
    description = fields.Text(string="Description")
    display = fields.Selection(
        [('default', 'Default'), ('products', 'Products'), ('subcategories', 'Subcategories'), ('both', 'Both')])
    menu_order = fields.Integer(string="Menu order")
    count = fields.Integer(string="Count")
    image_src = fields.Char(string="Image Src")

    def set_category_image(self, instance_id):
        """
        In this set category image from woocommerce to middle layer.
        :param instance_id: Browseable object of instance
        :return: Nothing
        """
        woo_api = instance_id
        try:  # Changes by Akash
            wcapi = woo_api.get_wcapi_connection()
        except Exception as e:
            return {"warning": {"message": (
                "{}".format(e))}}
        categories_response = wcapi.get('products/categories', params={'per_page': 20})
        if categories_response.status_code == 200:
            for woo_category_dict in categories_response.json():
                woo_product_categories_id = self.search(
                    [('instance_product_category_id', '=', woo_category_dict.get("id")),
                     ('instance_id', '=', woo_api.id)])
                if woo_product_categories_id:
                    if woo_category_dict.get('image'):
                        headers = {
                            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/39.0.2171.95 Safari/537.36'}
                        category_image_encoded = base64.b64encode(
                            requests.get(woo_category_dict.get('image')['src'], headers=headers).content)
                        woo_product_categories_id.write({
                            'category_image': category_image_encoded
                        })
        else:
            raise ValidationError("Sorry not get a Woocomerce Product Category Response")

    def import_product_category(self, instance_id, woo_categ_id=None, eg_category_id=None):
        """
        In this create odoo category and mapping category from woocommerce.
        :param instance_id: Browseable object of instance
        :param eg_category_id: Browseable object of mapping category
        :param woo_categ_id: id of woocommerce category
        :return: Nothing
        """
        status = "no"
        text = ""
        partial = False
        history_id_list = []
        woo_api = instance_id
        try:  # Changes by Akash
            wcapi = woo_api.get_wcapi_connection()
        except Exception as e:
            return {"warning": {"message": (
                "{}".format(e))}}
        if woo_categ_id:
            categories_response = wcapi.get("products/categories/{}".format(woo_categ_id))
        else:
            categories_response = wcapi.get('products/categories', params={'per_page': 20})
        if categories_response.status_code == 200:
            if woo_categ_id:
                categ_list = [categories_response.json()]
            else:
                categ_list = categories_response.json()
            for woo_category_dict in categ_list:
                if eg_category_id:
                    if woo_category_dict.get("name") == eg_category_id.name:
                        return woo_category_dict
                    else:
                        continue
                status = "no"
                history_category_id = None
                domain = []  # New Changes by akash start
                woo_parent_id = None
                if woo_category_dict.get("parent"):
                    woo_parent_id = self.search([('instance_product_category_id', '=', woo_category_dict.get("parent")),
                                                 ('instance_id', '=', woo_api.id)])
                    if woo_parent_id:
                        domain.append(("parent_id", "=", woo_parent_id.odoo_category_id.id))
                else:
                    domain.append(("parent_id", "in", ["", None, False]))

                odoo_product_categories_id = self.env['product.category'].search(
                    [('name', '=', woo_category_dict.get("name"))] + domain, limit=1)
                woo_product_categories_id = self.search(
                    [('instance_product_category_id', '=', woo_category_dict.get("id")),
                     ('instance_id', '=', woo_api.id)])
                #  New Changes by akash complete
                if odoo_product_categories_id and woo_product_categories_id:
                    status = "yes"
                    text = "This category is already mapping"
                    history_category_id = odoo_product_categories_id
                    _logging.info("{} already created!!!".format(woo_category_dict.get("name")))
                else:
                    if not odoo_product_categories_id:
                        data = {
                            'name': woo_category_dict.get("name"),
                            'product_count': woo_category_dict.get("count"),
                        }
                        if woo_parent_id:
                            data.update({"parent_id": woo_parent_id.odoo_category_id.id})
                        odoo_product_categories_id = self.env['product.category'].create(data)
                    if not woo_product_categories_id:
                        self.create([{
                            'instance_id': woo_api.id,
                            'instance_product_category_id': woo_category_dict.get("id"),
                            'name': woo_category_dict.get("name"),
                            'slug': woo_category_dict.get("slug"),
                            'description': woo_category_dict.get("description"),
                            'display': woo_category_dict.get("display"),
                            'menu_order': woo_category_dict.get("menu_order"),
                            'count': woo_category_dict.get("count"),
                            'parent_id': woo_category_dict.get("parent"),
                            'odoo_category_id': odoo_product_categories_id.id,
                            'real_parent_id': woo_parent_id and woo_parent_id.id or None,
                        }])
                    status = "yes"
                    text = "This category successfully crate and mapping"
                    history_category_id = odoo_product_categories_id
                eg_history_id = self.env["eg.sync.history"].create({"error_message": text,
                                                                    "status": status,
                                                                    "process_on": "category",
                                                                    "process": "a",
                                                                    "instance_id": woo_api.id,
                                                                    "category_id": history_category_id and history_category_id.id or None,
                                                                    "child_id": True})
                history_id_list.append(eg_history_id.id)
        else:
            text = "{}".format(categories_response.text)
        if partial:
            status = "partial"
            text = "Some category was created and some category is not create"
        if status == "yes" and not partial:
            text = "All category was successfully created"
        self.env["eg.sync.history"].create({"error_message": text,
                                            "status": status,
                                            "process_on": "category",
                                            "process": "a",
                                            "instance_id": woo_api and woo_api.id or None,
                                            "parent_id": True,
                                            "eg_history_ids": [(6, 0, history_id_list)]})

    def import_update_woo_product_category(self, instance_id):
        """
        In this update category of odoo and middle layer from woocommerce.
        :param instance_id: Browseable object of instance
        :return: Nothing
        """
        woo_api = instance_id
        try:  # Changes by Akash
            wcapi = woo_api.get_wcapi_connection()
        except Exception as e:
            return {"warning": {"message": (
                "{}".format(e))}}
        page = 1
        while page > 0:  # New Changes by akash
            categories_response = wcapi.get('products/categories', params={'per_page': 10, 'page': page})
            if categories_response.status_code == 200:
                if categories_response.json():
                    page += 1
                    for woo_category_dict in categories_response.json():
                        woo_product_categories_id = self.search(
                            [('instance_product_category_id', '=', woo_category_dict.get("id")),
                             ('instance_id', '=', woo_api.id)])
                        parent_id = self.search(
                            [('instance_product_category_id', '=', woo_category_dict.get("parent"))])
                        if woo_product_categories_id:
                            woo_product_categories_id.odoo_category_id.write(
                                {'name': woo_category_dict.get("name"),
                                 'product_count': woo_category_dict.get(
                                     "count"),
                                 "parent_id": parent_id and parent_id.odoo_category_id.id or None})
                            #  New Changes by akash
                            woo_product_categories_id.write({'instance_id': woo_api.id,
                                                             'name': woo_category_dict.get("name"),
                                                             'slug': woo_category_dict.get("slug"),
                                                             'description': woo_category_dict.get("description"),
                                                             'display': woo_category_dict.get("display"),
                                                             'menu_order': woo_category_dict.get("menu_order"),
                                                             'count': woo_category_dict.get("count"),
                                                             'parent_id': woo_category_dict.get("parent"),
                                                             'real_parent_id': parent_id and parent_id.id or None, })
                        else:
                            _logging.info("This category not created so please a import category first!!!")
                else:
                    break
            else:
                raise ValidationError("{}".format(categories_response.text))

    def export_woo_product_category(self, instance_id):
        """
        In this export from odoo category to woocommerce and middle layer.
        :param instance_id: Browseable object of instance
        :return: Nothing
        """
        status = "no"
        text = ""
        partial = False
        history_id_list = []
        woo_api = instance_id
        try:  # Changes by Akash
            wcapi = woo_api.get_wcapi_connection()
        except Exception as e:
            return {"warning": {"message": (
                "{}".format(e))}}
        odoo_category_ids = self.env['product.category'].search([])
        for product_category_id in odoo_category_ids:
            status = "no"
            #  Changes by Akash
            eg_product_category_id = self.search(
                [('odoo_category_id', '=', product_category_id.id), ("instance_id", "=", woo_api.id)])
            if eg_product_category_id:
                status = "yes"
                text = "This category is already exported"
                _logging.info("{} category already created!!!".format(product_category_id.name))
            else:
                woo_parent_category_id = None
                data = {'name': product_category_id.name,
                        'count': product_category_id.product_count, }
                if product_category_id.parent_id:  # Changes by Akash
                    woo_parent_category_id = self.search(
                        [('odoo_category_id', '=', product_category_id.parent_id.id),
                         ("instance_id", "=", woo_api.id)])
                    data.update({"parent": woo_parent_category_id.instance_product_category_id})
                woo_categories = wcapi.post("products/categories", data).json()
                if not woo_categories.get("data"):  # Changes by Akash
                    self.create([{'instance_product_category_id': woo_categories.get("id"),
                                  'odoo_category_id': product_category_id.id,
                                  'name': woo_categories.get("name"),
                                  'slug': woo_categories.get("slug"),
                                  'description': woo_categories.get("description"),
                                  'display': woo_categories.get("display"),
                                  'parent_id': woo_categories.get("parent"),
                                  'menu_order': woo_categories.get("menu_order"),
                                  'count': woo_categories.get("count"),  # Changes by Akash
                                  'real_parent_id': woo_parent_category_id and woo_parent_category_id.id or None,
                                  'instance_id': woo_api.id,  # Changes by Akash
                                  }])
                    status = "yes"
                    text = "This category is successfully export"
                else:
                    text = "{}".format(woo_categories.get("message"))
                    partial = True
                    _logging.info(  # Changes by Akash
                        "Export Category ({}) : {}".format(product_category_id.name, woo_categories.get("message")))
            eg_history_id = self.env["eg.sync.history"].create({"error_message": text,
                                                                "status": status,
                                                                "process_on": "category",
                                                                "process": "b",
                                                                "instance_id": woo_api.id,
                                                                "category_id": product_category_id.id,
                                                                "child_id": True})
            history_id_list.append(eg_history_id.id)
        if partial:
            status = "partial"
            text = "Some category was exported and some category is not exported"
        if status == "yes" and not partial:
            text = "All category was successfully exported"
        self.env["eg.sync.history"].create({"error_message": text,
                                            "status": status,
                                            "process_on": "category",
                                            "process": "b",
                                            "instance_id": woo_api and woo_api.id or None,
                                            "parent_id": True,
                                            "eg_history_ids": [(6, 0, history_id_list)]})

    def export_update_product_category(self, instance_id):
        """
        In this update category from odoo to woocommerce and middle layer.
        :param instance_id: Browseable object of instance
        :return: Nothing
        """
        woo_api = instance_id
        try:  # Changes by Akash
            wcapi = woo_api.get_wcapi_connection()
        except Exception as e:
            return {"warning": {"message": (
                "{}".format(e))}}
        odoo_category_ids = self.env['product.category'].search([])
        for product_category_id in odoo_category_ids:
            eg_product_category_id = self.search(
                [('odoo_category_id', '=', product_category_id.id), ("instance_id", "=", woo_api.id)], limit=1)
            if eg_product_category_id:
                woo_parent_category_id = None
                data = {'name': product_category_id.name,
                        'count': product_category_id.product_count, }
                if product_category_id.parent_id:  # Changes by Akash
                    woo_parent_category_id = self.search(
                        [('odoo_category_id', '=', product_category_id.parent_id.id),
                         ("instance_id", "=", woo_api.id)], limit=1)
                    data.update({"parent": woo_parent_category_id.instance_product_category_id})
                response = wcapi.put(
                    "products/categories/{}".format(eg_product_category_id.instance_product_category_id),
                    data)
                if response.status_code == 200:  # Changes by Akash
                    response = response.json()
                    data = {'slug': response.get("slug"),
                            'description': response.get("description"),
                            'display': response.get("display"),
                            'parent_id': response.get("parent"),
                            'menu_order': response.get("menu_order"),
                            'count': response.get("count"), }  # Changes by Akash
                    if woo_parent_category_id:
                        data.update({'real_parent_id': woo_parent_category_id.id})
                    eg_product_category_id.write(data)  # Changes by Akash
                else:
                    _logging.info("{}".format(response.text))
            else:
                _logging.info("{} Category not created so first export Category".format(product_category_id.name))
