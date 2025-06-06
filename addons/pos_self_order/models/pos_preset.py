from odoo import models, api, fields


class PosPreset(models.Model):
    _inherit = "pos.preset"

    available_in_self = fields.Boolean(string='Available in self', default=False)
    service_at = fields.Selection(
        [("counter", "Pickup zone"), ("table", "Table"), ("delivery", "Delivery")],
        string="Service at",
        default="counter",
        required=True,
    )

    # will be overridden.
    @api.model
    def _load_pos_self_data_domain(self, data, config):
        return ['|', ('id', '=', config.default_preset_id.id), '&', ('available_in_self', '=', True), ('id', 'in', config.available_preset_ids.ids)]

    @api.model
    def _load_pos_self_data_fields(self, config):
        params = super()._load_pos_self_data_fields(config)
        params.append('service_at')
        return params
