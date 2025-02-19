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
    def _load_pos_self_data_domain(self, data):
        config_id = data['pos.config'][0]['available_preset_ids']
        return ['|', ('id', '=', data['pos.config'][0]['default_preset_id']), '&', ('available_in_self', '=', True), ('id', 'in', config_id)]

    @api.model
    def _load_pos_self_data_fields(self, config_id):
        params = super()._load_pos_self_data_fields(config_id)
        params.extend(['service_at', 'mail_template_id'])
        return params
    
    @api.model
    def _load_pos_data_fields(self, config_id):
        params = super()._load_pos_data_fields(config_id)
        params.extend(['mail_template_id'])
        return params
