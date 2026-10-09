import logging

from odoo import models, fields
from odoo.exceptions import ValidationError

_logging = logging.getLogger("===+++ eCom Product Attribute +++===")  # Changes by Akash


class EgProductAttribute(models.Model):
    _inherit = 'eg.product.attribute'

    slug = fields.Char(string='Slug')
    type = fields.Char(string='Type')
    order_by = fields.Char(string='Order By')
    has_archives = fields.Boolean(string="Has Archieve")
    eg_product_tmpl_id = fields.Many2one(comodel_name='eg.product.template')

    def import_update_product_attribute(self, instance_id):
        """
        In this update odoo attribute and mapping attribute from woocommerce.
        :param instance_id: Browseable object of instance
        :return: Nothing
        """
        woo_api = instance_id
        try:  # Changes by Akash
            wcapi = woo_api.get_wcapi_connection()
        except Exception as e:
            return {"warning": {"message": (
                "{}".format(e))}}
        attribute_response = wcapi.get('products/attributes')
        if attribute_response.status_code == 200:
            for woo_attribute_dict in attribute_response.json():
                eg_attribute_id = self.search(
                    [('inst_attribute_id', '=', str(woo_attribute_dict.get("id"))), ('instance_id', '=', woo_api.id)])
                if eg_attribute_id:
                    eg_attribute_id.odoo_attribute_id.write({'name': woo_attribute_dict.get("name"), })
                    eg_attribute_id.write({'inst_attribute_id': str(woo_attribute_dict.get("id")),
                                           'name': woo_attribute_dict.get("name"),
                                           'slug': woo_attribute_dict.get("slug"),
                                           'type': woo_attribute_dict.get("type"),
                                           'order_by': woo_attribute_dict.get("order_by"),
                                           'has_archives': woo_attribute_dict.get("has_archives"),
                                           'instance_id': woo_api.id, })
                else:
                    _logging.info(
                        "This {} attribute not created so first import attribute!!!".format(
                            woo_attribute_dict.get('name')))
        else:
            raise ValidationError("{}".format(attribute_response.text))

    def export_update_product_attribute(self, instance_id):
        """
        in this method update attribute from odoo to woocommerce and middle layer.
        :param instance_id: Browseable object of instance
        :return: Nothing
        """
        woo_api = instance_id
        try:  # Changes by Akash
            wcapi = woo_api.get_wcapi_connection()
        except Exception as e:
            return {"warning": {"message": (
                "{}".format(e))}}
        odoo_product_attribute_ids = self.env['product.attribute'].search([])
        for odoo_product_attribute_id in odoo_product_attribute_ids:
            eg_attribute_id = self.search(
                [('odoo_attribute_id', '=', odoo_product_attribute_id.id), ("instance_id", "=", instance_id.id)])
            if eg_attribute_id:
                data = {'name': odoo_product_attribute_id.name, }
                response = wcapi.put("products/attributes/{}".format(eg_attribute_id.id), data)
                if response.status_code == 200:  # Changes by Akash
                    eg_attribute_id = response.json()
                    eg_attribute_id.update({'name': eg_attribute_id.get("name"),
                                            'slug': eg_attribute_id.get("slug"),
                                            'type': eg_attribute_id.get("type"),
                                            'order_by': eg_attribute_id.get("order_by"),
                                            'has_archives': eg_attribute_id.get("has_archives"), })
                else:
                    _logging.info(
                        "Update Export Attribute - ({}) : {}".format(odoo_product_attribute_id.name, response.text))
            else:
                _logging.info("{} attribute not created so first export Product attribute!!!".format(
                    odoo_product_attribute_id.name))

    def import_attribute(self, instance_id=None, eg_product_attribute_id=None):
        """
        In this method create odoo attribute and mapping attribute when import attribute from woocommerce.
        :param instance_id: Browseable object of instance
        :param eg_product_attribute_id:  Browseable object of mapping attribute
        :return: Nothing
        """
        status = "no"  # History code add by akash
        text = ""
        partial = False
        history_id_list = []
        woo_api = instance_id
        try:  # Changes by Akash
            wcapi = woo_api.get_wcapi_connection()
        except Exception as e:
            return {"warning": {"message": (
                "{}".format(e))}}
        attribute_response = wcapi.get('products/attributes')
        if attribute_response.status_code == 200:
            for woo_attribute_dict in attribute_response.json():
                if eg_product_attribute_id:
                    if woo_attribute_dict.get("name") == eg_product_attribute_id.name:
                        return woo_attribute_dict
                    else:
                        continue
                eg_attribute_id = self.search(
                    [('inst_attribute_id', '=', str(woo_attribute_dict.get("id"))), ('instance_id', '=', woo_api.id)])
                odoo_attribute_id = self.env['product.attribute'].search(
                    [('name', '=', woo_attribute_dict.get("name"))])

                if odoo_attribute_id and eg_attribute_id:
                    status = "yes"
                    text = "This attribute is already mapping"
                    _logging.info("{} attribute already created !!!".format(woo_attribute_dict.get("name")))
                else:
                    if not odoo_attribute_id:
                        odoo_attribute_id = self.env['product.attribute'].create(
                            {'name': woo_attribute_dict.get("name"), })
                    if not eg_attribute_id:
                        self.create([{'inst_attribute_id': str(woo_attribute_dict.get("id")),
                                      'name': woo_attribute_dict.get("name"),
                                      'slug': woo_attribute_dict.get("slug"),
                                      'type': woo_attribute_dict.get("type"),
                                      'order_by': woo_attribute_dict.get("order_by"),
                                      'has_archives': woo_attribute_dict.get("has_archives"),
                                      'odoo_attribute_id': odoo_attribute_id.id,
                                      'instance_id': woo_api.id,
                                      }])
                    status = "yes"
                    text = "This attribute is successfully create and mapping"
                eg_history_id = self.env["eg.sync.history"].create({"error_message": text,
                                                                    "status": status,
                                                                    "process_on": "attribute",
                                                                    "process": "a",
                                                                    "instance_id": woo_api.id,
                                                                    "attribute_id": odoo_attribute_id and odoo_attribute_id.id or None,
                                                                    "child_id": True})
                history_id_list.append(eg_history_id.id)

            if partial:
                status = "partial"
                text = "Some attribute was created and some attribute is not create"
            if status == "yes" and not partial:
                text = "All attribute was successfully created"
            self.env["eg.sync.history"].create({"error_message": text,
                                                "status": status,
                                                "process_on": "attribute",
                                                "process": "a",
                                                "instance_id": woo_api.id,
                                                "parent_id": True,
                                                "eg_history_ids": [(6, 0, history_id_list)]})
        else:
            raise ValidationError('Not get a response of a Woocommerce')

    def export_product_attribute(self, instance_id):
        """
        In this export attribute to woocommerce and mapping attribute.
        :param instance_id: Browseable object of instance
        :return: Nothing
        """
        status = "no"  # History code add by akash
        text = ""
        partial = False
        history_id_list = []
        woo_api = instance_id
        try:  # Changes by Akash
            wcapi = woo_api.get_wcapi_connection()
        except Exception as e:
            return {"warning": {"message": (
                "{}".format(e))}}
        odoo_product_attribute_ids = self.env['product.attribute'].search([])
        for odoo_product_attribute_id in odoo_product_attribute_ids:
            status = "no"
            #  Changes by Akash
            eg_attribute_id = self.search(
                [('odoo_attribute_id', '=', odoo_product_attribute_id.id), ("instance_id", "=", woo_api.id)])
            if eg_attribute_id:
                status = "yes"
                text = "This attribute is already exported"
                _logging.info("{} attribute already exported!!!".format(odoo_product_attribute_id.name))
            else:
                data = {'name': odoo_product_attribute_id.name, }
                eg_attribute_id = wcapi.post("products/attributes", data)
                if eg_attribute_id.status_code == 200:  # Changes by Akash
                    eg_attribute_id = eg_attribute_id.json()
                    self.create([{'name': eg_attribute_id.get("name"),
                                  'inst_attribute_id': str(eg_attribute_id.get("id")),
                                  'slug': eg_attribute_id.get("slug"),
                                  'type': eg_attribute_id.get("type"),
                                  'order_by': eg_attribute_id.get("order_by"),
                                  'has_archives': eg_attribute_id.get("has_archives"),
                                  'odoo_attribute_id': odoo_product_attribute_id.id,
                                  'instance_id': woo_api.id}])
                    status = "yes"
                    text = "This attribute is successfully export"
                else:  # Changes by Akash
                    text = "{}".format(eg_attribute_id.text)
                    partial = True
                    _logging.info("Export Attribute - ({}) : {}".format(odoo_product_attribute_id.name,
                                                                        eg_attribute_id.text))
            eg_history_id = self.env["eg.sync.history"].create({"error_message": text,
                                                                "status": status,
                                                                "process_on": "attribute",
                                                                "process": "b",
                                                                "instance_id": woo_api.id,
                                                                "attribute_id": odoo_product_attribute_id.id,
                                                                "child_id": True})
            history_id_list.append(eg_history_id.id)

        if partial:
            status = "partial"
            text = "Some attribute was export and some attribute is not export"
        if status == "yes" and not partial:
            text = "All attribute was successfully exported"
        self.env["eg.sync.history"].create({"error_message": text,
                                            "status": status,
                                            "process_on": "attribute",
                                            "process": "b",
                                            "instance_id": woo_api.id,
                                            "parent_id": True,
                                            "eg_history_ids": [(6, 0, history_id_list)]})
