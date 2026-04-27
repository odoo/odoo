# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, api
from odoo.exceptions import ValidationError


class EnviaShippingWizard(models.TransientModel):
    _name = "envia.shipping.wizard"
    _description = "Choose from the available Envia.com shipping methods"

    carrier_id = fields.Many2one(
        comodel_name='delivery.carrier',
        string="Delivery",
    )
    available_services = fields.Json(
        string="Available Services",
        help="Contains the list of available services for the Envia.com account to select from.",
        export_string_translation=False,
    )
    selected_service_code = fields.Char(string="Selected Service")
    selected_carrier_code = fields.Char(string="Selected Carrier")

    @api.constrains('selected_service_code', 'selected_carrier_code')
    def _check_codes(self):
        for record in self:
            for service in record.available_services:
                if service['name'] == record.selected_service_code and service['carrier_name'] == record.selected_carrier_code:
                    break
            else:
                raise ValidationError(self.env._("Carriers and Services must be selected from the list of available shipping methods."))

    def action_validate(self):
        self.ensure_one()
        selected_service = next(
            service for service in self.available_services
            if service['name'] == self.selected_service_code
            if service['carrier_name'] == self.selected_carrier_code
        )
        self.carrier_id.write({
            'envia_service_code': selected_service['name'],
            'envia_carrier_code': selected_service['carrier_name'],
            'envia_service_name': f"{selected_service['carrier_name'].upper()}: {selected_service['description']} ({selected_service['name']})",
        })
