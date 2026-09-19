from odoo import api, fields, models

ROOM_KIND = "room"


class ResourceAsset(models.Model):
    _inherit = "resource.asset"

    room_short_code = fields.Char(
        related="resource_id.short_code",
        string="Short Code",
        readonly=False,
    )
    room_booking_url = fields.Char(
        related="resource_id.room_booking_url",
        string="Room Link",
    )
    room_bookable_background_color = fields.Char(
        related="resource_id.bookable_background_color",
        string="Available Background Color",
        readonly=False,
    )
    room_booked_background_color = fields.Char(
        related="resource_id.booked_background_color",
        string="Booked Background Color",
        readonly=False,
    )
    room_background_image = fields.Image(
        related="resource_id.room_background_image",
        string="Background Image",
        readonly=False,
    )
    room_is_available = fields.Boolean(
        related="resource_id.is_available",
        string="Is Room Currently Available",
    )
    room_next_booking_start = fields.Datetime(
        related="resource_id.next_booking_start",
        string="Next Booking Start",
    )

    @api.depends("kind_id", "address_id.name")
    def _compute_display_name(self):
        super()._compute_display_name()
        for asset in self:
            if asset.kind_id.code == ROOM_KIND and asset.name and asset.address_id:
                asset.display_name = f"{asset.address_id.name} - {asset.name}"

    def _on_kind_changed(self, vals):
        super()._on_kind_changed(vals)
        self._make_rooms_bookable()

    def _write_concrete(self, vals):
        res = super()._write_concrete(vals)
        if {"name", "description", "active"} & vals.keys():
            for room in self.resource_id.filtered("access_token"):
                room._notify_booking_view("reload")
        return res

    def _make_rooms_bookable(self):
        rooms = self.filtered(lambda asset: asset.kind_id.code == ROOM_KIND)
        if rooms:
            rooms.sudo().resource_id._setup_room_kiosk()

    def action_view_room_booking_view(self):
        self.check_singleton()
        return self.resource_id.action_view_booking_view()

    def action_view_room_bookings(self):
        self.check_singleton()
        return self.resource_id.action_view_bookings()
