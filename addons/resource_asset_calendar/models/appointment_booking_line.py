from odoo import api, models
from odoo.exceptions import ValidationError


class AppointmentBookingLine(models.Model):
    _inherit = "appointment.booking.line"

    @api.constrains("resource_id")
    def _check_asset_bookable(self):
        states = None
        for line in self:
            asset = line.sudo().resource_id.asset_id
            if not asset or asset._accepts_bookings():
                continue
            states = states or dict(
                asset._fields["state"]._description_selection(self.env)
            )
            raise ValidationError(
                self.env._(
                    "%(asset)s cannot be booked while it is %(state)s.",
                    asset=asset.display_name,
                    state=states[asset.state].lower(),
                )
            )
