# -- coding: utf-8 --
###############################################################################
#
#    Cybrosys Technologies Pvt. Ltd.
#    Copyright (C) 2023-TODAY Cybrosys Technologies(<https://www.cybrosys.com>)
#    Author: Cybrosys (<https://www.cybrosys.com>)
#
#    This program is free software: you can modify
#    it under the terms of the GNU Affero General Public License (AGPL) as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <https://www.gnu.org/licenses/>.
#
###############################################################################
from odoo import api, fields, models


class ResConfigSettings(models.TransientModel):
    """Inheriting ResConfigSettings Model.
        This class extends the functionality of the 'res.config.settings'
        model.It allows customizing and managing configuration settings
        for the module """
    _inherit = 'res.config.settings'

    is_billing_phone = fields.Boolean(
        string="Billing Phone",
        config_parameter='website_sale_address_management.is_billing_phone',
        help="Enable or disable the option for billing phone")
    is_billing_phone_is_required = fields.Boolean(
        string="Billing Phone Required",
        config_parameter='website_sale_address_management'
                         '.is_billing_phone_is_required',
        help="Specify whether billing phone is required")
    is_billing_street = fields.Boolean(
        string="Billing Street",
        config_parameter='website_sale_address_management.is_billing_street',
        help="Enable or disable the option for billing street")
    is_billing_street_is_required = fields.Boolean(
        string="Billing Street Is Required",
        config_parameter='website_sale_address_management.'
                         'is_billing_street_is_required',
        help="Specify whether billing street is required")
    is_billing_street2 = fields.Boolean(
        string="Billing Street 2",
        config_parameter='website_sale_address_management.is_billing_street2',
        help="Enable or disable the option for billing street 2")
    is_billing_city = fields.Boolean(
        string="Billing City",
        config_parameter='website_sale_address_management.is_billing_city',
        help="Enable or disable the option for billing city")
    is_billing_city_is_required = fields.Boolean(
        string="Billing City Is Required",
        config_parameter='website_sale_address_management'
                         '.is_billing_city_is_required',
        help="Specify whether billing city is required")
    billing_country_id = fields.Many2one('res.country',
                                         config_parameter='billing_country',
                                         string="Default Billing Country",
                                         help="Specify default billing country")
    is_billing_zip_code = fields.Boolean(
        string="Billing ZIP Code",
        config_parameter='website_sale_address_management.is_billing_zip_code',
        help="Enable or disable the option for billing ZIP code")
    is_billing_zip_code_is_required = fields.Boolean(
        string="Billing ZIP Code Is Required",
        config_parameter='website_sale_address_management.'
                         'is_billing_zip_code_is_required',
        help="Specify whether billing ZIP code is required")
    is_shipping_phone = fields.Boolean(
        string="Shipping Phone",
        config_parameter='website_sale_address_management.is_shipping_phone',
        help="Enable or disable the option for shipping phone")
    is_shipping_phone_is_required = fields.Boolean(
        string="Shipping Phone Is Required",
        config_parameter='website_sale_address_management.'
                         'is_shipping_phone_is_required',
        help="Specify whether shipping phone is required")
    is_shipping_street = fields.Boolean(
        string="Shipping Street",
        config_parameter='website_sale_address_management.is_shipping_street',
        help="Enable or disable the option for shipping street")
    is_shipping_street_is_required = fields.Boolean(
        string="Shipping Street Is Required",
        config_parameter='website_sale_address_management.'
                         'is_shipping_street_is_required',
        help="Specify whether shipping street is required")
    is_shipping_street2 = fields.Boolean(
        string="Shipping Street 2",
        config_parameter='website_sale_address_management.is_shipping_street2',
        help="Enable or disable the option for shipping street 2")
    is_shipping_city = fields.Boolean(
        string="Shipping City",
        config_parameter='website_sale_address_management.is_shipping_city',
        help="Enable or disable the option for shipping city")
    is_shipping_city_is_required = fields.Boolean(
        string="Shipping City Is Required",
        config_parameter='website_sale_address_management.'
                         'is_shipping_city_is_required',
        help="Specify whether shipping city is required")
    shipping_country_id = fields.Many2one('res.country',
                                          config_parameter='shipping_country',
                                          string="Default Shipping Country",
                                          help="Specify the default "
                                               "shipping country")
    is_shipping_zip_code = fields.Boolean(
        string="Shipping ZIP Code",
        config_parameter='website_sale_address_management.is_shipping_zip_code',
        help="Enable or disable the option for shipping ZIP code")
    is_shipping_zip_code_is_required = fields.Boolean(
        string="Shipping ZIP Code Is Required",
        config_parameter='website_sale_address_management.'
                         'is_shipping_zip_code_is_required',
        help="Specify whether shipping ZIP code is required")

    @api.onchange('is_billing_phone', 'is_billing_street', 'is_billing_city',
                  'is_billing_zip_code', 'is_shipping_phone',
                  'is_shipping_street', 'is_shipping_city',
                  'is_shipping_zip_code')
    def _onchange_fields(self):
        """This method is triggered when any of the specified fields
         are changed. It updates the corresponding required fields based on
         the user's input."""
        if not self.is_billing_phone:
            self.is_billing_phone_is_required = False
        if not self.is_billing_street:
            self.is_billing_street_is_required = False
        if not self.is_billing_city:
            self.is_billing_city_is_required = False
        if not self.is_billing_zip_code:
            self.is_billing_zip_code_is_required = False
        if not self.is_shipping_phone:
            self.is_shipping_phone_is_required = False
        if not self.is_shipping_street:
            self.is_shipping_street_is_required = False
        if not self.is_shipping_city:
            self.is_shipping_city_is_required = False
        if not self.is_shipping_zip_code:
            self.is_shipping_zip_code_is_required = False
