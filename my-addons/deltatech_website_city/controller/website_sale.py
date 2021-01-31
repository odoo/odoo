# ©  2015-2020 Deltatech
#              Dorin Hongu <dhongu(@)gmail(.)com
# See README.rst file on addons root folder for license details

from odoo.http import request

from odoo.addons.website_sale.controllers.main import WebsiteSale


class WebsiteSaleCity(WebsiteSale):

    # pentru tarile in care nu avam nomencator de localitati nu se poate face acest camp obligatori
    # def _get_mandatory_billing_fields(self):
    #     res = super(WebsiteSaleCity, self)._get_mandatory_billing_fields()
    #     res += ['city_id']
    #     res.remove('city')
    #     return res
    #
    # def _get_mandatory_shipping_fields(self):
    #     res = super(WebsiteSaleCity, self)._get_mandatory_shipping_fields()
    #     res += ['city_id']
    #     res.remove('city')
    #     return res

    def values_postprocess(self, order, mode, values, errors, error_msg):
        new_values, errors, error_msg = super(WebsiteSaleCity, self).values_postprocess(
            order, mode, values, errors, error_msg
        )
        new_values["city_id"] = values.get("city_id")
        if new_values["city_id"]:
            city = request.env["res.city"].browse(int(values.get("city_id")))
            if city:
                new_values["city"] = city.name
        return new_values, errors, error_msg

    def checkout_form_validate(self, mode, all_form_values, data):
        error, error_message = super(WebsiteSaleCity, self).checkout_form_validate(mode, all_form_values, data)

        # Check if city_id required
        country = request.env["res.country"]
        if data.get("country_id"):
            country = country.browse(int(data.get("country_id")))
            if country.enforce_cities:
                if error.get("city") == "missing":
                    del error["city"]
                    error["city_id"] = "missing"
                if not data.get("city_id"):
                    error["city_id"] = "missing"

        return error, error_message
