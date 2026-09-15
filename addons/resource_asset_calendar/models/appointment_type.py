from odoo import models


class AppointmentType(models.Model):
    _inherit = "appointment.type"

    def _slot_availability_is_resource_available(
        self, slot, resource, availability_values
    ):
        asset = resource.sudo().asset_id
        if asset and not asset._is_bookable():
            return False
        return super()._slot_availability_is_resource_available(
            slot, resource, availability_values
        )
