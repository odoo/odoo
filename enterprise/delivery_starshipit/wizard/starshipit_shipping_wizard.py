# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, _


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

        if self.env.context.get('create_new_carrier') and (order_vals := self.env.context.get('order_vals')):
            new_carrier_id = self.carrier_id.copy()
            new_carrier_id.write({
                'name': f"{selected_service['carrier_name']}: {selected_service['service_name']} ({selected_service['service_code']})",
                'starshipit_service_code': selected_service['service_code'],
                'starshipit_carrier_code': selected_service['carrier'],
                'starshipit_service_name': f"{selected_service['carrier_name']}: {selected_service['service_name']} ({selected_service['service_code']})",
            })
            view_id = self.env.ref('delivery.choose_delivery_carrier_view_form').id
            return {
                'name': _('Add a shipping method'),
                'type': 'ir.actions.act_window',
                'view_mode': 'form',
                'res_model': 'choose.delivery.carrier',
                'view_id': view_id,
                'views': [(view_id, 'form')],
                'target': 'new',
                'context': {
                    'default_carrier_id': new_carrier_id.id,
                    'default_order_id': order_vals.get('order_id'),
                    'default_total_weight': order_vals.get('total_weight'),
                }
            }

        else:
            self.carrier_id.write({
                'starshipit_service_code': selected_service['service_code'],
                'starshipit_carrier_code': selected_service['carrier'],
                'starshipit_service_name': f"{selected_service['carrier_name']}: {selected_service['service_name']} ({selected_service['service_code']})",
            })
