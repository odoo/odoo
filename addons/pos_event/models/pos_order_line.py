from odoo import api, fields, models


class PosOrderLine(models.Model):
    _inherit = "pos.order.line"

    event_ticket_id = fields.Many2one("event.event.ticket")
    event_registration_ids = fields.One2many(
        "event.registration", "pos_order_line_id", string="Event Registrations"
    )

    @api.model
    def _load_pos_data_fields(self, config):
        fields = super()._load_pos_data_fields(config)
        fields += ["event_ticket_id", "event_registration_ids"]
        return fields
