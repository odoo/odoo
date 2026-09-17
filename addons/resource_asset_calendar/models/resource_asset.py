from odoo import fields, models

BOOKABLE_STATES = ("in_service", "maintenance")


class ResourceAsset(models.Model):
    _inherit = "resource.asset"

    appointment_type_ids = fields.Many2many(
        related="resource_id.appointment_type_ids",
        readonly=False,
    )
    is_bookable = fields.Boolean(related="resource_id.is_bookable")

    def _accepts_bookings(self):
        self.check_singleton()
        return self.state in BOOKABLE_STATES
