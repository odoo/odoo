import logging
import re
from odoo import fields, models
from odoo.exceptions import UserError

_logging = logging.getLogger(__name__)


class WooTaxRate(models.Model):
    _name = 'woo.tax.rate'
    _description = 'Woocommrece Tax Rate'

    instance_id = fields.Many2one(comodel_name='eg.ecom.instance', required=True)
    provider = fields.Selection(related="instance_id.provider", store=True)
    woo_tax_rate_id = fields.Integer(string="WC Tax Rate ID")
    odoo_tax_rate_id = fields.Many2one(comodel_name='account.tax', required=True)
    name = fields.Char(string="Name")
    country_iso_code = fields.Char(string="Country Code")
    state_code = fields.Char(string="State Code")
    tax_rate = fields.Char(string="Rate")
    tax_priority = fields.Integer(string="Tax Priority")
    compound_rate = fields.Boolean(string="Compound Rate")
    is_shipping_tax = fields.Boolean(string="Shipping Tax Applied")
    tax_order = fields.Integer(string="Order")
    tax_class = fields.Char(string="Tax Class")
    real_tax_class_id = fields.Many2one(comodel_name='woo.tax.class', string='Tax Class ID')

    def import_update_tax_rate(self, instance_id):
        """
        In this update tax from woocommerce to odoo and middle layer.
        :param instance_id: Browseable object of instance
        :return: Nothing
        """
        woo_api = instance_id
        try:  # Changes by Akash
            wcapi = woo_api.get_wcapi_connection()
        except Exception as e:
            raise UserError("{}".format(e))
        tax_rates_response = wcapi.get('taxes')
        if tax_rates_response.status_code == 200:  # Changes by Akash
            for woo_tax_rate_dict in tax_rates_response.json():
                woo_tax_rate_id = self.search(
                    [('instance_id', '=', woo_api.id), '|', ("woo_tax_rate_id", "=", woo_tax_rate_dict.get("id")),
                     ("name", "=", woo_tax_rate_dict.get("name"))])
                if woo_tax_rate_id:
                    tax_class_id = self.env['woo.tax.class'].search([('slug', '=', woo_tax_rate_dict.get("class"))])
                    woo_tax_rate_id.odoo_tax_rate_id.write({'name': woo_tax_rate_dict.get("name"),
                                                            'amount': woo_tax_rate_dict.get("rate"), })
                    woo_tax_rate_id.write({
                        'name': woo_tax_rate_dict.get("name"),
                        'country_iso_code': woo_tax_rate_dict.get("country"),
                        'state_code': woo_tax_rate_dict.get("state"),
                        'tax_rate': woo_tax_rate_dict.get("rate"),
                        'tax_priority': woo_tax_rate_dict.get("priority"),
                        'compound_rate': woo_tax_rate_dict.get("compound"),
                        'is_shipping_tax': woo_tax_rate_dict.get("shipping"),
                        'tax_order': woo_tax_rate_dict.get("order"),
                        'tax_class': woo_tax_rate_dict.get("class"),
                        'real_tax_class_id': tax_class_id.id,
                    })
                else:
                    _logging.info(
                        "{} tax rate not created so first import tax rate!!!".format(woo_tax_rate_dict.get("name")))
        else:
            raise UserError("{}".format(tax_rates_response.text))

    def export_update_tax_rate(self, instance_id):
        """
        In this update tax from odoo to middle layer and woocommerce
        :param instance_id: Browseable object of instance
        :return: Nothing
        """
        woo_api = instance_id
        try:  # Changes by Akash
            wcapi = woo_api.get_wcapi_connection()
        except Exception as e:
            raise UserError("{}".format(e))

        odoo_tax_rate_ids = self.env['account.tax'].search([])
        for odoo_tax_rate_id in odoo_tax_rate_ids:
            woo_tax_rate_id = self.search(
                [('odoo_tax_rate_id', '=', odoo_tax_rate_id.id), ("instance_id", "=", woo_api.id)])

            if woo_tax_rate_id:
                data = {'name': odoo_tax_rate_id.name,
                        'rate': str(odoo_tax_rate_id.amount), }
                odoo_taxes = wcapi.put("taxes/{}".format(woo_tax_rate_id.woo_tax_rate_id), data)
                if odoo_taxes.status_code == 200:  # Changes by Akash
                    woo_tax_id = odoo_taxes.json()
                    woo_tax_rate_id.write({'name': woo_tax_id.get("name"),
                                           'tax_rate': woo_tax_id.get("rate")})  # Changes by Akash
                else:  # Changes by Akash
                    _logging.info("Update Export tax rate - ({}) : {}".format(odoo_tax_rate_id.name, odoo_taxes.text))
            else:
                _logging.info("{} not created so first export tax rate".format(odoo_tax_rate_id.name))

    def import_woo_tax_rate(self, instance_id=None, woo_tax_id=None):
        """
        In this create odoo tax and mapping tax from woocommerce
        :param instance_id: Browseable object of instance
        :param woo_tax_id: Id of woo tax
        :return: Nothing
        """
        woo_api = instance_id
        try:  # Changes by Akash
            wcapi = woo_api.get_wcapi_connection()
        except Exception as e:
            raise UserError("{}".format(e))
        if woo_tax_id:
            tax_rates_response = wcapi.get("taxes/{}".format(woo_tax_id))
        else:
            tax_rates_response = wcapi.get('taxes')
        if tax_rates_response.status_code == 200:
            if woo_tax_id:
                woo_tax_list = [tax_rates_response.json()]
            else:
                woo_tax_list = tax_rates_response.json()
            for woo_tax_rate_dict in woo_tax_list:
                if not float(woo_tax_rate_dict.get("rate")):
                    continue
                woo_tax_rate_id = self.search(
                    [('instance_id', '=', woo_api.id), '|', ("woo_tax_rate_id", "=", woo_tax_rate_dict.get("id")),
                     ("name", "=", woo_tax_rate_dict.get("name"))])
                if not woo_tax_rate_id:
                    tax_class_id = self.env['woo.tax.class'].search(
                        [('slug', '=', woo_tax_rate_dict.get("class")), ('instance_id', '=', woo_api.id)])
                    if not tax_class_id:
                        self.env['woo.tax.class'].import_woo_tax_class(instance_id=woo_api)
                        tax_class_id = self.env['woo.tax.class'].search(
                            [('slug', '=', woo_tax_rate_dict.get("class")), ('instance_id', '=', woo_api.id)])
                    rate = float(woo_tax_rate_dict.get("rate"))
                    pure_name = "".join(re.split("[^a-zA-Z]*", woo_tax_rate_dict.get("name")))
                    name = "{} {}%".format(pure_name, round(rate, 2))
                    if pure_name == "GST":
                        odoo_tax_id = self.env["account.tax"].search(
                            [("name", "=", name), ("amount_type", "=", "group"), ("type_tax_use", "=", "sale")],
                            limit=1)
                    elif pure_name == "IGST":
                        odoo_tax_id = self.env["account.tax"].search(
                            [("name", "=", name), ("amount", "=", rate), ("amount_type", "=", "percent"),
                             ("type_tax_use", "=", "sale")], limit=1)
                    else:
                        odoo_tax_id = self.env["account.tax"].search(
                            [("name", "=", woo_tax_rate_dict.get("name")), ("amount", "=", rate),
                             ("amount_type", "=", "percent"),
                             ("type_tax_use", "=", "sale")], limit=1)

                    if not odoo_tax_id:
                        if pure_name == "GST":
                            sgst_tax_group_id = self.env["account.tax.group"].search([("name", "=", "SGST")])
                            cgst_tax_group_id = self.env["account.tax.group"].search([("name", "=", "CGST")])
                            half_rate = rate / 2
                            children_tax_list = [(0, 0, {"name": "SGST Sale {}%".format(half_rate),
                                                         "amount_type": "percent",
                                                         "amount": half_rate,
                                                         "type_tax_use": "none",
                                                         "tax_group_id": sgst_tax_group_id.id,
                                                         "description": "SGST {}%".format(half_rate)}),
                                                 (0, 0, {"name": "CGST Sale {}%".format(half_rate),
                                                         "amount_type": "percent",
                                                         "type_tax_use": "none",
                                                         "amount": half_rate,
                                                         "tax_group_id": cgst_tax_group_id.id,
                                                         "description": "CGST {}%".format(half_rate)})]
                            odoo_tax_id = self.env["account.tax"].create({"name": name,
                                                                          "amount": rate,
                                                                          "amount_type": "group",
                                                                          "type_tax_use": "sale",
                                                                          "children_tax_ids": children_tax_list,
                                                                          "description": name})
                        elif pure_name == "IGST":
                            tax_group_id = self.env["account.tax.group"].search([("name", "=", pure_name)], limit=1)
                            if not tax_group_id:
                                tax_group_id = self.env["account.tax.group"].create({"name": pure_name})
                            odoo_tax_id = self.env["account.tax"].create({"name": name,
                                                                          "amount": rate,
                                                                          "amount_type": "percent",
                                                                          "type_tax_use": "sale",
                                                                          "tax_group_id": tax_group_id.id,
                                                                          "description": name
                                                                          })
                        else:
                            tax_group_id = self.env["account.tax.group"].search([("name", "=", pure_name[:4])], limit=1)
                            if not tax_group_id:
                                tax_group_id = self.env["account.tax.group"].create({"name": pure_name[:4]})
                            odoo_tax_id = self.env["account.tax"].create({"name": woo_tax_rate_dict.get("name"),
                                                                          "amount": rate,
                                                                          "amount_type": "percent",
                                                                          "tax_group_id": tax_group_id.id,
                                                                          "type_tax_use": "sale",
                                                                          "description": woo_tax_rate_dict.get("name")})
                    woo_tax_rate_id = self.create([{'instance_id': woo_api.id,
                                                    'woo_tax_rate_id': woo_tax_rate_dict.get("id"),
                                                    'name': woo_tax_rate_dict.get("name"),
                                                    'country_iso_code': woo_tax_rate_dict.get("country"),
                                                    'state_code': woo_tax_rate_dict.get("state"),
                                                    'tax_rate': woo_tax_rate_dict.get("rate"),
                                                    'tax_priority': woo_tax_rate_dict.get("priority"),
                                                    'compound_rate': woo_tax_rate_dict.get("compound"),
                                                    'is_shipping_tax': woo_tax_rate_dict.get("shipping"),
                                                    'tax_order': woo_tax_rate_dict.get("order"),
                                                    'tax_class': woo_tax_rate_dict.get("class"),
                                                    'real_tax_class_id': tax_class_id.id,
                                                    'odoo_tax_rate_id': odoo_tax_id.id,
                                                    }])
                    if woo_tax_id:
                        return woo_tax_rate_id
                else:
                    _logging.info("{} tax rate is a already created".format(woo_tax_rate_dict.get("name")))
                    if woo_tax_id:
                        return woo_tax_rate_id
        else:
            raise UserError("{}".format(tax_rates_response.text))

    def export_tax_rate(self, instance_id):
        """
        In this export tax from odoo to woocommerce and middle layer.
        :param instance_id: Browseable object of instance
        :return: Nothing
        """
        woo_api = instance_id
        try:  # Changes by Akash
            wcapi = woo_api.get_wcapi_connection()
        except Exception as e:
            raise UserError("{}".format(e))

        odoo_tax_rate_ids = self.env['account.tax'].search([("type_tax_use", "=", "sale")])
        for odoo_tax_rate_id in odoo_tax_rate_ids:
            woo_tax_rate_id = self.search(
                [('odoo_tax_rate_id', '=', odoo_tax_rate_id.id), ("instance_id", "=", woo_api.id)])

            if woo_tax_rate_id:
                _logging.info("{} tax rate is already created!!!".format(odoo_tax_rate_id.name))
            else:
                data = {'name': odoo_tax_rate_id.name,
                        'rate': str(odoo_tax_rate_id.amount), }
                woo_tax_id = wcapi.post("taxes", data)
                if woo_tax_id.status_code == 201:  # Changes by Akash
                    woo_tax_id = woo_tax_id.json()
                    self.create([{'woo_tax_rate_id': woo_tax_id.get("id"),
                                  'odoo_tax_rate_id': odoo_tax_rate_id.id,
                                  'name': woo_tax_id.get("name"),
                                  'instance_id': instance_id.id,
                                  'tax_rate': woo_tax_id.get("rate"), }])
                else:  # Changes by Akash
                    _logging.info("Export Tax Rate - ({}) : {}".format(odoo_tax_rate_id.name, woo_tax_id.text))
