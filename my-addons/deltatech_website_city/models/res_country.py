# ©  2015-2020 Deltatech
# See README.rst file on addons root folder for license details


from odoo import fields, models


class CountryState(models.Model):
    _inherit = "res.country.state"

    city_ids = fields.One2many("res.city", "state_id")

    def get_website_sale_cities(self, mode="billing"):
        return self.sudo().city_ids
