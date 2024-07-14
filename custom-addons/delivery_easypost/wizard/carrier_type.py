# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models

class CarrierType(models.TransientModel):
    _name = "delivery.carrier.easypost"
    _description = "Carrier Type"

    # This selection field gets its values from a custom widget: CarrierTypeSelection
    carrier_type = fields.Char()
    delivery_carrier_id = fields.Many2one('delivery.carrier')

    def action_validate(self):
        if self.delivery_carrier_id.easypost_delivery_type != self.carrier_type:
            # Update delivery carrier with selected type.
            self.delivery_carrier_id.easypost_delivery_type = self.carrier_type
            self.delivery_carrier_id.easypost_delivery_type_id = self.env.context['carrier_types'][self.carrier_type]

            self.delivery_carrier_id.easypost_delivery_type = self.carrier_type
            self.delivery_carrier_id.easypost_default_package_type_id = False
            self.delivery_carrier_id.easypost_default_service_id = False

        # Contact the proxy in order to get the predefined
        # package type proposed on the easypost website
        # https://www.easypost.com/docs/api.html#predefined-packages
        package_types_by_carriers, services_by_carriers = self.env['delivery.carrier']._easypost_get_services_and_package_types()
        package_types = package_types_by_carriers.get(self.carrier_type)
        services = services_by_carriers.get(self.carrier_type)
        if package_types:
            already_existing_packages = self.env['stock.package.type'].search_read([
                ('package_carrier_type', '=', 'easypost'),
                ('easypost_carrier', '=', self.carrier_type),
                ('shipper_package_code', 'in', package_types),
                ('name', 'in', package_types)
            ], ['name'])
            # Difference between the package types already
            # present in the database and the new one fetched
            # on the easypost documentation page.
            for package_type in set(package_types) ^ set([package['name'] for package in already_existing_packages]):
                self.env['stock.package.type'].create({
                    'name': package_type,
                    'package_carrier_type': 'easypost',
                    'shipper_package_code': package_type,
                    'easypost_carrier': self.carrier_type,
                })
        if services:
            # Same as package types but for service
            # level https://www.easypost.com/docs/api.html#service-levels
            already_existing_services = self.env['easypost.service'].search_read([
                ('easypost_carrier', '=', self.carrier_type),
                ('name', 'in', services)
            ], ['name'])
            for service in set(services) ^ set([service['name'] for service in already_existing_services]):
                self.env['easypost.service'].create({
                    'name': service,
                    'easypost_carrier': self.carrier_type,
                })
        # Open the delivery carrier form view in edit mode,
        # the purpose is to force the user to set a package
        # type in order to get dimension. Mandatory for
        # shipment API request.
        action = self.env["ir.actions.actions"]._for_xml_id("delivery.action_delivery_carrier_form")
        action['res_id'] = self.delivery_carrier_id.id
        action['views'] = [(self.env.ref('delivery.view_delivery_carrier_form').id, 'form')]
        return action
