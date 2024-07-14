# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class StarshipitShippingWizard(models.TransientModel):
    _name = "starshipit.shipping.wizard"
    _description = "Choose from the available starshipit shipping methods"

    carrier_id = fields.Many2one(
        comodel_name='delivery.carrier',
        string="Delivery",
    )
    available_services = fields.Json(
        string="Available Services",
        help="Contains the list of available services for the starshipit account to select from.",
        export_string_translation=False,
    )
    selected_service_code = fields.Char(string="Selected Service")

    def action_validate(self):
        self.ensure_one()
        selected_service = next(iter([
            service for service in self.available_services if service['service_code'] == self.selected_service_code
        ]))
        self.carrier_id.write({
            'starshipit_service_code': selected_service['service_code'],
            'starshipit_carrier_code': selected_service['carrier'],
            'starshipit_service_name': f"{selected_service['carrier_name']}: {selected_service['service_name']} ({selected_service['service_code']})",
        })
