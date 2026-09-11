import base64
import logging

import requests

from odoo import models, fields
from odoo.exceptions import ValidationError

_logging = logging.getLogger("===+++ eCom Customer +++===")


class EgResPartner(models.Model):
    _inherit = 'eg.res.partner'

    email = fields.Char(string="Email")
    first_name = fields.Char(string="First Name")
    last_name = fields.Char(string="Last Name")
    customer_role = fields.Char(string="Customer Role")
    username = fields.Char(string="Username")

    billing_first_name = fields.Char("First Name")
    billing_last_name = fields.Char("Last Name")
    billing_company = fields.Char("Company Name")
    billing_address_1 = fields.Char("Billing Address-1")
    billing_address_2 = fields.Char("Billing Address-2")
    billing_city = fields.Char("City")
    billing_postcode = fields.Char("Postcode")
    billing_country = fields.Char("Country")
    billing_state = fields.Char("State")
    billing_email = fields.Char("Email")
    billing_phone = fields.Char("Phone")

    shipping_first_name = fields.Char("First Name")
    shipping_last_name = fields.Char("Last Name")
    shipping_company = fields.Char("Company")
    shipping_address_1 = fields.Char("Address-1")
    shipping_address_2 = fields.Char("Address-2")
    shipping_city = fields.Char("City")
    shipping_state = fields.Char("State")
    shipping_postcode = fields.Char("Postal Code")
    shipping_country = fields.Char("Country")

    is_paying_customer = fields.Boolean("Paying Customer")

    def set_customer_image(self, instance_id=None):
        """
        In this method when import customer so set image woocommerce to middle layer.
        :params instance_id: Browseable object
        :return: Nothing
        """
        woo_api = instance_id
        try:  # TODO : Changes by Akash
            wcapi = woo_api.get_wcapi_connection()
        except Exception as e:
            return {"warning": {"message": (
                "{}".format(e))}}
        page = 1
        while page > 0:
            customer_response = wcapi.get('customers', params={'per_page': 100, 'page': page})
            if customer_response.status_code == 200:
                if not customer_response.json():
                    break
                page += 1
                for woo_customer in customer_response.json():
                    eg_customer_id = self.search(
                        [('inst_partner_id', '=', str(woo_customer.get("id"))), ('instance_id', '=', woo_api.id)])
                    if eg_customer_id:
                        if woo_customer.get('avatar_url'):
                            headers = {
                                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/39.0.2171.95 Safari/537.36'}
                            customer_image_encoded = base64.b64encode(
                                requests.get(woo_customer.get('avatar_url'), headers=headers).content)
                            eg_customer_id.write({
                                'customer_image': customer_image_encoded
                            })
            else:
                raise ValidationError("{}".format(customer_response.text))

    def create_customer_in_woocommerce(self, woo_customer, woo_api):
        """
        In this method create record for mapping customer.
        :param woo_customer: Dict of customer data
        :param woo_api: Browseable object
        :return: Browseable object of Mapping Customer
        """
        odoo_partner_id = self.env['res.partner'].search([('email', '=', woo_customer.get("email"))])
        eg_customer_id = self.env['eg.res.partner'].create({'instance_id': woo_api.id,
                                                            'inst_partner_id': str(woo_customer.get("id")),
                                                            'email': woo_customer.get("email"),
                                                            'first_name': woo_customer.get("first_name"),
                                                            'last_name': woo_customer.get("last_name"),
                                                            'customer_role': woo_customer.get("role"),
                                                            'username': woo_customer.get("username"),
                                                            'odoo_partner_id': odoo_partner_id.id,
                                                            'billing_first_name': woo_customer.get("billing").get(
                                                                "first_name") or "",
                                                            'billing_last_name': woo_customer.get("billing").get(
                                                                "last_name") or "",
                                                            'billing_company': woo_customer.get("billing").get(
                                                                "company") or "",
                                                            'billing_address_1': woo_customer.get("billing").get(
                                                                "address_1") or "",
                                                            'billing_address_2': woo_customer.get("billing").get(
                                                                "address_2"),
                                                            'billing_city': woo_customer.get("billing").get(
                                                                "city") or "",
                                                            'billing_postcode': woo_customer.get("billing")[
                                                                                    "postcode"] or "",
                                                            'billing_country': woo_customer.get("billing")[
                                                                                   "country"] or "",
                                                            'billing_state': woo_customer.get("billing")[
                                                                                 "state"] or "",
                                                            'billing_email': woo_customer.get('billing')[
                                                                                 "email"] or "",
                                                            'billing_phone': woo_customer.get('billing')[
                                                                                 "phone"] or "",

                                                            'shipping_first_name': woo_customer.get("shipping")[
                                                                                       "first_name"] or "",
                                                            'shipping_last_name': woo_customer.get("shipping")[
                                                                                      "last_name"] or "",
                                                            'shipping_company': woo_customer.get("shipping")[
                                                                                    "company"] or "",
                                                            'shipping_address_1': woo_customer.get("shipping")[
                                                                                      "address_1"] or "",
                                                            'shipping_address_2': woo_customer.get("shipping")[
                                                                                      "address_2"] or "",
                                                            'shipping_city': woo_customer.get("shipping")[
                                                                                 "city"] or "",
                                                            'shipping_state': woo_customer.get("shipping")[
                                                                                  "state"] or "",
                                                            'shipping_postcode': woo_customer.get("shipping")[
                                                                                     "postcode"] or "",
                                                            'shipping_country': woo_customer.get("shipping")[
                                                                                    "country"] or "",
                                                            })
        return eg_customer_id

    def create_customer_in_odoo(self, woo_customer):
        """
        In this method create record for odoo customer and his child customer.
        :param woo_customer: Dict of customer data
        :return: Browseable object of odoo Customer
        """
        odoo_country_id = self.env['res.country'].search(
            [('code', '=', woo_customer.get("billing")["country"])])
        odoo_state_id = self.env['res.country.state'].search(
            [('country_id', '=', odoo_country_id.id), ('code', '=', woo_customer.get("billing")["state"])])
        full_name = woo_customer.get('first_name') + " " + woo_customer.get('last_name')
        odoo_partner_id = self.env['res.partner'].create({'name': full_name,
                                                          'email': woo_customer.get('email') or "",
                                                          'street': woo_customer.get("billing")["address_1"] or "",
                                                          'street2': woo_customer.get("billing")["address_2"] or "",
                                                          'city': woo_customer.get("billing")["city"] or "",
                                                          'country_id': odoo_country_id.id,
                                                          'state_id': odoo_state_id.id,
                                                          'zip': woo_customer.get("billing")['postcode'] or "",
                                                          'phone': woo_customer.get("billing")['phone'] or "",
                                                          })
        odoo_shipping_country_id = self.env['res.country'].search(
            [('code', '=', woo_customer.get("shipping")["country"])])
        odoo_shipping_state_id = self.env['res.country.state'].search(
            [('country_id', '=', odoo_shipping_country_id.id), ('code', '=', woo_customer.get("shipping")["state"])])
        full_name = woo_customer.get("shipping")["first_name"] + " " + \
                    woo_customer.get("shipping")[
                        "last_name"]
        odoo_partner_child_id = self.env['res.partner'].create({'parent_id': odoo_partner_id.id,
                                                                'name': full_name,
                                                                'type': 'other',
                                                                'street': woo_customer.get("shipping")["address_1"],
                                                                'street2': woo_customer.get("shipping")["address_2"],
                                                                'city': woo_customer.get("shipping")["city"],
                                                                'country_id': odoo_shipping_country_id.id,
                                                                'state_id': odoo_shipping_state_id.id,
                                                                'zip': woo_customer.get("shipping")['postcode'],
                                                                })
        return odoo_partner_id

    def import_customer(self, instance_id, woo_customer_dict=None):
        """
        In this method when import customer so create odoo customer and mapping customer.
        :param instance_id: Browseable object
        :param woo_customer_dict: Dict of customer data
        :return: list of Browseable object for billing partner, shipping partner and customer
        """
        status = "no"  # History code add by akash
        text = ""
        partial = False
        history_id_list = []
        woo_api = instance_id
        try:  # TODO : Changes by Akash
            wcapi = woo_api.get_wcapi_connection()
        except Exception as e:
            return {"warning": {"message": (
                "{}".format(e))}}
        if woo_customer_dict:
            customer_response = wcapi.get('customers/{}'.format(woo_customer_dict.get('customer_id')))
        else:
            customer_response = wcapi.get('customers', params={'per_page': 100})
        if customer_response.status_code == 200:
            if woo_customer_dict:
                customer_list = [customer_response.json()]
            else:
                customer_list = customer_response.json()
            for woo_customer in customer_list:
                status = "no"
                res_partner_id = None
                customer_list_sale = []
                eg_customer_id = self.search(
                    [('inst_partner_id', '=', str(woo_customer.get("id"))), ('instance_id', '=', woo_api.id)])

                if eg_customer_id:
                    odoo_partner_id = eg_customer_id.odoo_partner_id
                    default_address = woo_customer.get("billing")
                    new_partner_id = self.comparison_partner_address(eg_customer_id=eg_customer_id,
                                                                     odoo_partner_id=odoo_partner_id,
                                                                     woo_customer=woo_customer, woo_api=woo_api,
                                                                     default_address=default_address)
                    status = "yes"
                    text = "This Customer is already mapped"
                    res_partner_id = odoo_partner_id

                else:
                    odoo_partner_id = self.env['res.partner'].search([('email', '=', woo_customer.get('email'))])
                    if odoo_partner_id:
                        default_address = woo_customer.get("billing")
                        new_partner_id = self.comparison_partner_address(eg_customer_id=None,
                                                                         odoo_partner_id=odoo_partner_id,
                                                                         woo_customer=woo_customer, woo_api=woo_api,
                                                                         default_address=default_address)

                    else:
                        if any(woo_customer.get("billing").values()) and any(woo_customer.get("shipping").values()):
                            odoo_partner_id = self.create_customer_in_odoo(woo_customer)
                    if odoo_partner_id:
                        eg_customer_id = self.create_customer_in_woocommerce(woo_customer, woo_api)
                        status = "yes"
                        text = "This Customer was created"
                        res_partner_id = odoo_partner_id
                    else:
                        partial = True
                        text = "Customer Was not created"
                if woo_customer_dict:
                    customer_list_sale.append(odoo_partner_id)
                    if woo_customer_dict.get("billing"):
                        default_address = woo_customer_dict.get("billing")
                        billing_partner = self.comparison_partner_address(eg_customer_id=True,
                                                                          odoo_partner_id=odoo_partner_id,
                                                                          woo_customer=woo_customer, woo_api=woo_api,
                                                                          default_address=default_address)
                        customer_list_sale.append(billing_partner)
                    if woo_customer_dict.get("shipping"):
                        default_address = woo_customer_dict.get("shipping")
                        shipping_partner = self.comparison_partner_address(eg_customer_id=True,
                                                                           odoo_partner_id=odoo_partner_id,
                                                                           woo_customer=woo_customer, woo_api=woo_api,
                                                                           default_address=default_address)
                        customer_list_sale.append(shipping_partner)
                    return customer_list_sale
                eg_history_id = self.env["eg.sync.history"].create({"error_message": text,
                                                                    "status": status,
                                                                    "process_on": "customer",
                                                                    "process": "a",
                                                                    "instance_id": woo_api.id,
                                                                    "partner_id": res_partner_id and res_partner_id.id or None,
                                                                    "child_id": True})
                history_id_list.append(eg_history_id.id)

            if partial:
                status = "partial"
                text = "Some customer was created and some customer is not create"
            if status == "yes" and not partial:
                text = "All customer was successfully created"
            self.env["eg.sync.history"].create({"error_message": text,
                                                "status": status,
                                                "process_on": "customer",
                                                "process": "a",
                                                "instance_id": instance_id and instance_id.id or None,
                                                "parent_id": True,
                                                "eg_history_ids": [(6, 0, history_id_list)]})
        else:
            raise ValidationError("{}".format(customer_response.text))

    def comparison_partner_address(self, odoo_partner_id=None, eg_customer_id=None, woo_customer=None, woo_api=None,
                                   default_address=None):
        """
        In this method check odoo customer address and bigcommerce default address sem or not and create child partner.
        and not mapping customer so create mapping customer.
        :param odoo_partner_id: Browseable object of odoo customer
        :param eg_customer_id: Browseable object of mapping customer
        :param woo_customer: Dict of customer data
        :param woo_api: Browseable object of instance
        :param default_address: Dictionary of address data
        :return: Browseable object of Child customer or parent customer
        """
        if not eg_customer_id and odoo_partner_id:
            self.create_customer_in_woocommerce(woo_customer, woo_api)
        partner_information = {"name": odoo_partner_id.name or "",
                               "phone": odoo_partner_id.phone or "",
                               "street": odoo_partner_id.street or "",
                               "street2": odoo_partner_id.street2 or "",
                               "city": odoo_partner_id.city or "",
                               "zip": odoo_partner_id.zip or "",
                               "country_id": odoo_partner_id.country_id and odoo_partner_id.country_id.code or "",
                               "state_id": odoo_partner_id.state_id and odoo_partner_id.state_id.code or ""}
        woo_partner_information = {
            "name": default_address.get('first_name') + " " + default_address.get(
                'last_name'),
            "phone": default_address.get('phone') or "",
            "street": default_address.get('address_1') or "",
            "street2": default_address.get('address_2') or "",
            "city": default_address.get('city') or "",
            "zip": default_address.get('postcode') or "",
            "country_id": default_address.get('country') or "",
            "state_id": default_address.get('state') or ""}

        if partner_information == woo_partner_information:
            _logging.info("{} customer in odoo".format(woo_customer.get('username')))
            return odoo_partner_id
        else:
            create_child = False
            if odoo_partner_id.child_ids:
                for partner_child_id in odoo_partner_id.child_ids:
                    child_partner_information = {"name": partner_child_id.name or "",
                                                 "phone": partner_child_id.phone or "",
                                                 "street": partner_child_id.street or "",
                                                 "street2": partner_child_id.street2 or "",
                                                 "city": partner_child_id.city or "",
                                                 "zip": partner_child_id.zip or "",
                                                 "country_id": partner_child_id.country_id and partner_child_id.country_id.code or "",
                                                 "state_id": partner_child_id.state_id and partner_child_id.state_id.code or ""}
                    if child_partner_information == woo_partner_information:
                        _logging.info("{} user is already in odoo")
                        return partner_child_id
                    else:
                        create_child = True
            if not odoo_partner_id.child_ids or create_child:
                country_id = self.env['res.country'].search([('code', '=', default_address.get('country'))])
                state_id = self.env['res.country.state'].search(
                    [('country_id', '=', country_id.id), ('code', '=', default_address.get('state'))])
                if not state_id:
                    state_id = self.env['res.country.state'].create({'country_id': country_id.id,
                                                                     'name': default_address.get('state'),
                                                                     'code': default_address.get('state'),
                                                                     })
                odoo_child_id = self.env['res.partner'].create({'parent_id': odoo_partner_id.id,
                                                                'name': default_address.get(
                                                                    'first_name') + " " + default_address.get(
                                                                    'last_name'),
                                                                'type': 'other',
                                                                "phone": default_address.get('phone') or "",
                                                                "street": default_address.get('address_1') or "",
                                                                "street2": default_address.get('address_2') or "",
                                                                "city": default_address.get('city') or "",
                                                                "zip": default_address.get('postcode') or "",
                                                                "country_id": country_id.id,
                                                                "state_id": state_id.id,
                                                                })
                return odoo_child_id
