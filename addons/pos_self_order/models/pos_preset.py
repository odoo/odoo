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
    
    mail_template_id = fields.Many2one(
        string="Email Confirmation",
        comodel_name='mail.template',
        domain="[('model', '=', 'pos.order')]",
    )

    # will be overridden.
    @api.model
    def _load_pos_self_data_domain(self, data, config):
        return ['|', ('id', '=', config.default_preset_id.id), '&', ('available_in_self', '=', True), ('id', 'in', config.available_preset_ids.ids)]

    @api.model
    def _load_pos_self_data_fields(self, config):
        params = super()._load_pos_self_data_fields(config)
        params.extend(['service_at', 'mail_template_id'])
        return params
    
    @api.model
    def _load_pos_data_fields(self, config):
        params = super()._load_pos_data_fields(config)
        params.extend(['mail_template_id'])
        return params

    def _can_return_content(self, field_name=None, access_token=None):
        if field_name in ["image_128", "image_512"]:
            return True
        return super()._can_return_content(field_name, access_token)
