import logging
from odoo import fields
from odoo import models

_logging = logging.getLogger("===+++ eCom Attribute Value +++===")  # : Changes by Akash


class EgAttributeValue(models.Model):
    _inherit = 'eg.attribute.value'

    slug = fields.Char(string="Slug")
    description = fields.Text(string="Description")
    menu_order = fields.Integer(string="Menu Order")
    count = fields.Integer(string="Count")

    def import_update_attribute_terms(self, instance_id):
        """
        In this update attribute value of odoo and mapping from woocommerce.
        :param instance_id: Browseable object of instance
        :return: Nothing
        """
        woo_api = instance_id
        try:  # : Changes by Akash
            wcapi = woo_api.get_wcapi_connection()
        except Exception as e:
            raise Warning("{}".format(e))
        eg_attribute_ids = self.env['eg.product.attribute'].search([("instance_id", "=", woo_api.id)])
        for eg_attribute_id in eg_attribute_ids:
            attribute_terms_response = wcapi.get(
                "products/attributes/{}/terms".format(eg_attribute_id.inst_attribute_id))
            if attribute_terms_response.status_code == 200:
                for woo_terms_dict in attribute_terms_response.json():
                    eg_value_id = self.search(
                        [('name', '=', woo_terms_dict.get("name")), ('instance_id', '=', woo_api.id),
                         ("inst_attribute_id", "=", eg_attribute_id.id)])
                    if eg_value_id:
                        eg_value_id.odoo_attribute_value_id.write({'name': woo_terms_dict.get("name"),
                                                                   'attribute_id': eg_attribute_id.odoo_attribute_id.id,
                                                                   })
                        eg_value_id.write({'name': woo_terms_dict.get("name"),
                                           'instance_value_id': woo_terms_dict.get("id"),
                                           'slug': woo_terms_dict.get("slug"),
                                           'description': woo_terms_dict.get("description"),
                                           'menu_order': woo_terms_dict.get("menu_order"),
                                           'count': woo_terms_dict.get("count"),
                                           'instance_id': woo_api.id,
                                           })
                    else:
                        _logging.info("The {} attribute terms not created so please import first!!!".format(
                            woo_terms_dict.get("name")))
            else:
                raise Warning("{}".format(attribute_terms_response.text))

    def export_update_attribute_term(self, instance_id):
        """
        In this update attribute value from odoo to woocommerce and middle layer.
        :param instance_id: Browseable object of instance
        :return: Nothing
        """
        woo_api = instance_id
        try:  # : Changes by Akash
            wcapi = woo_api.get_wcapi_connection()
        except Exception as e:
            raise Warning("{}".format(e))
        woo_product_attributes_ids = self.env['eg.product.attribute'].search([("instance_id", "=", woo_api.id)])
        for eg_attribute_id in woo_product_attributes_ids:
            for woo_value_id in eg_attribute_id.eg_value_ids:
                data = {'name': woo_value_id.odoo_attribute_value_id.name, }
                response = wcapi.put(
                    "products/attributes/{}/terms/{}".format(eg_attribute_id.inst_attribute_id,
                                                             woo_value_id.instance_value_id), data)
                if response.status_code == 200:
                    woo_term_id = response.json()
                    woo_value_id.write({'name': woo_term_id.get('name'),
                                        'slug': woo_term_id.get('slug'),
                                        'description': woo_term_id.get('description'),
                                        'menu_order': woo_term_id.get('menu_order'),
                                        'count': woo_term_id.get('count'),
                                        })
                else:
                    _logging.info("Update Export Terms - ({}) : {}".format(woo_value_id.odoo_attribute_value_id.name,
                                                                           response.text))

    def import_product_attribute_terms(self, instance_id):
        """
        In this create odoo attribute value and mapping value when import attribute value
        :param instance_id: Browseable object of instance
        :return: Nothing
        """
        status = "no"  # TODO: History code add by akash
        text = ""
        partial = False
        history_id_list = []
        woo_api = instance_id
        try:  # : Changes by Akash
            wcapi = woo_api.get_wcapi_connection()
        except Exception as e:
            raise Warning("{}".format(e))
        eg_attribute_ids = self.env['eg.product.attribute'].search([('instance_id', '=', woo_api.id)])
        for eg_attribute_id in eg_attribute_ids:
            status = "no"
            attribute_terms_response = wcapi.get(
                "products/attributes/{}/terms".format(eg_attribute_id.inst_attribute_id))
            if attribute_terms_response.status_code == 200:
                term_list = []
                for woo_terms_dict in attribute_terms_response.json():
                    eg_value_id = self.search(
                        [('name', '=', woo_terms_dict.get("name")), ('instance_id', '=', woo_api.id),
                         ("inst_attribute_id", "=", eg_attribute_id.id)])  # : New Changes by akash
                    odoo_attribute_term_id = self.env['product.attribute.value'].search(
                        [('name', '=', woo_terms_dict.get("name")),
                         ("attribute_id", "=", eg_attribute_id.odoo_attribute_id.id)])  # : New Changes by akash

                    if eg_value_id and odoo_attribute_term_id:
                        _logging.info("{} terms already created!!!".format(woo_terms_dict.get("name")))
                    else:
                        if not odoo_attribute_term_id:
                            odoo_attribute_term_id = self.env['product.attribute.value'].create({
                                'name': woo_terms_dict.get('name'),
                                'attribute_id': eg_attribute_id.odoo_attribute_id.id
                            })
                        if not eg_value_id:
                            self.create([{
                                'name': woo_terms_dict.get("name"),
                                'instance_value_id': woo_terms_dict.get("id"),
                                'slug': woo_terms_dict.get("slug"),
                                'description': woo_terms_dict.get("description"),
                                'menu_order': woo_terms_dict.get("menu_order"),
                                'count': woo_terms_dict.get("count"),
                                'odoo_attribute_value_id': odoo_attribute_term_id.id,
                                'inst_attribute_id': eg_attribute_id.id,
                                'instance_id': woo_api.id,
                            }])
                    term_list.append(woo_terms_dict.get("name"))
                term_list = ",".join(term_list)
                status = "yes"
                text = "This attribute values are successfully create : {}".format(term_list)
            else:
                partial = True
                text = "{}".format(attribute_terms_response.text)
            eg_history_id = self.env["eg.sync.history"].create({"error_message": text,
                                                                "status": status,
                                                                "process_on": "attribute",
                                                                "process": "a",
                                                                "instance_id": woo_api.id,
                                                                "attribute_id": eg_attribute_id.odoo_attribute_id.id,
                                                                "child_id": True})
            history_id_list.append(eg_history_id.id)
        if partial:
            status = "partial"
            text = "Some attribute values was created and some attribute values is not create"
        if status == "yes" and not partial:
            text = "All attribute values was successfully created"
        self.env["eg.sync.history"].create({"error_message": text,
                                            "status": status,
                                            "process_on": "attribute",
                                            "process": "a",
                                            "instance_id": woo_api.id,
                                            "parent_id": True,
                                            "eg_history_ids": [(6, 0, history_id_list)]})

    def export_woo_product_attribute_terms(self, instance_id):
        """
        In this export attribute value from odoo to woocommerce and middle layer.
        :param instance_id: Browseable object of instance
        :return: Nothing
        """
        status = "no"
        text = ""
        partial = False
        history_id_list = []
        woo_api = instance_id
        try:  # : Changes by Akash
            wcapi = woo_api.get_wcapi_connection()
        except Exception as e:
            raise Warning("{}".format(e))
        # : Changes by Akash
        woo_product_attributes_ids = self.env['eg.product.attribute'].search([("instance_id", "=", woo_api.id)])
        for eg_attribute_id in woo_product_attributes_ids:
            term_list = []
            new_term_list = []
            term_partial = False
            for woo_value_id in eg_attribute_id.odoo_attribute_id.value_ids:
                woo_attribute_value_id = self.search(
                    [('name', '=', woo_value_id.name), ("instance_id", "=", woo_api.id),
                     ("inst_attribute_id", "=", eg_attribute_id.id)])  # : Changes by Akash
                if woo_attribute_value_id:
                    term_list.append(woo_value_id.name)
                    _logging.info("{} already created!!!".format(woo_value_id.name))
                else:
                    data = {'name': woo_value_id.name, }
                    woo_term_id = wcapi.post(
                        "products/attributes/{}/terms".format(eg_attribute_id.inst_attribute_id), data)
                    if woo_term_id.status_code == 200:  # : Changes by Akash
                        woo_term_id = woo_term_id.json()
                        self.create([{'instance_value_id': woo_term_id.get('id'),
                                      'odoo_attribute_value_id': woo_value_id.id,
                                      'name': woo_term_id.get('name'),
                                      'slug': woo_term_id.get('slug'),
                                      'description': woo_term_id.get('description'),
                                      'menu_order': woo_term_id.get('menu_order'),
                                      'count': woo_term_id.get('count'),
                                      'instance_id': woo_api.id,  # : Changes by Akash
                                      }])
                        term_list.append(woo_value_id.name)
                    else:
                        term_partial = True
                        new_term_list.append(woo_value_id.name)
                        _logging.info(
                            "Export Attribute Value - ({}) : {}".format(woo_value_id.name, woo_term_id.text))
            if term_partial:
                text = "This attribute value successfully export : {} and This attribute value not export : {}".format(
                    ",".join(term_list), ",".join(new_term_list))
                status = "partial"
                partial = True
            else:
                status = "yes"
                text = "All attribute value successfully export : {}".format(",".join(term_list))
            eg_history_id = self.env["eg.sync.history"].create({"error_message": text,
                                                                "status": status,
                                                                "process_on": "attribute",
                                                                "process": "b",
                                                                "instance_id": woo_api.id,
                                                                "attribute_id": eg_attribute_id.odoo_attribute_id.id,
                                                                "child_id": True})
            history_id_list.append(eg_history_id.id)
        if partial:
            status = "partial"
            text = "Some attribute values was exported and some attribute values is not exported"
        if status == "yes" and not partial:
            text = "All attribute values was successfully exported"
        self.env["eg.sync.history"].create({"error_message": text,
                                            "status": status,
                                            "process_on": "attribute",
                                            "process": "b",
                                            "instance_id": woo_api.id,
                                            "parent_id": True,
                                            "eg_history_ids": [(6, 0, history_id_list)]})
